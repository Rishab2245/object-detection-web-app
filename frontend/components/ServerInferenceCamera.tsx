import { useRef, useState, useEffect, useLayoutEffect } from 'react';
import Webcam from 'react-webcam';
import { yoloClasses } from '../data/yolo_classes';
import { round } from 'lodash';

interface ServerInferenceCameraProps {
  width: number;
  height: number;
  modelName: string;
  currentModelResolution: number[];
  changeCurrentModelResolution: (width?: number, height?: number) => void;
  serverUrl: string;
}

interface Detection {
  label: string;
  score: number;
  xmin: number;
  ymin: number;
  xmax: number;
  ymax: number;
}

interface ServerResponse {
  frame_id: string;
  capture_ts: number;
  recv_ts: number;
  inference_ts: number;
  detections: Detection[];
}

const ServerInferenceCamera = (props: ServerInferenceCameraProps) => {
  const [inferenceTime, setInferenceTime] = useState<number>(0);
  const [totalTime, setTotalTime] = useState<number>(0);
  const [networkLatency, setNetworkLatency] = useState<number>(0);
  const [serverLatency, setServerLatency] = useState<number>(0);
  const webcamRef = useRef<Webcam>(null);
  const videoCanvasRef = useRef<HTMLCanvasElement>(null);
  const liveDetection = useRef<boolean>(false);
  const frameCounter = useRef<number>(0);

  const [facingMode, setFacingMode] = useState<string>('environment');
  const originalSize = useRef<number[]>([0, 0]);

  const [modelResolution, setModelResolution] = useState<number[]>(
    props.currentModelResolution
  );

  const [SSR, setSSR] = useState<Boolean>(true);

  useEffect(() => {
    setModelResolution(props.currentModelResolution);
  }, [props.currentModelResolution]);

  // close camera when browser tab is minimized
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        liveDetection.current = false;
      }
      // set SSR to true to prevent webcam from loading when tab is not active
      setSSR(document.hidden);
    };
    setSSR(document.hidden);
    document.addEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const setWebcamCanvasOverlaySize = () => {
    const element = webcamRef.current!.video!;
    if (!element) return;
    var w = element.offsetWidth;
    var h = element.offsetHeight;
    var cv = videoCanvasRef.current;
    if (!cv) return;
    cv.width = w;
    cv.height = h;
  };

  const capture = () => {
    const canvas = videoCanvasRef.current!;
    const context = canvas.getContext('2d', {
      willReadFrequently: true,
    })!;

    if (facingMode === 'user') {
      context.setTransform(-1, 0, 0, 1, canvas.width, 0);
    }

    context.drawImage(
      webcamRef.current!.video!,
      0,
      0,
      canvas.width,
      canvas.height
    );

    if (facingMode === 'user') {
      context.setTransform(1, 0, 0, 1, 0, 0);
    }
    return context;
  };

  const sendFrameToServer = async (ctx: CanvasRenderingContext2D): Promise<ServerResponse | null> => {
    try {
      const canvas = ctx.canvas;
      const imageData = canvas.toDataURL('image/jpeg', 0.8);
      const frameId = `frame_${frameCounter.current++}`;
      const captureTs = Date.now();

      const payload = {
        frame_id: frameId,
        capture_ts: captureTs,
        image_data: imageData,
        model_name: props.modelName,
        resolution: modelResolution
      };

      const response = await fetch(`${props.serverUrl}/api/detect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result: ServerResponse = await response.json();
      
      // Calculate latencies
      const now = Date.now();
      const networkLat = result.recv_ts - result.capture_ts;
      const serverLat = result.inference_ts - result.recv_ts;
      const totalLat = now - result.capture_ts;
      
      setNetworkLatency(networkLat);
      setServerLatency(serverLat);
      setInferenceTime(serverLat);
      
      return result;
    } catch (error) {
      console.error('Error sending frame to server:', error);
      return null;
    }
  };

  const conf2color = (conf: number) => {
    const r = Math.round(255 * (1 - conf));
    const g = Math.round(255 * conf);
    return `rgb(${r},${g},0)`;
  };

  const drawDetections = (ctx: CanvasRenderingContext2D, detections: Detection[]) => {
    const canvas = ctx.canvas;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    detections.forEach(detection => {
      const { label, score, xmin, ymin, xmax, ymax } = detection;
      
      // Convert normalized coordinates to canvas coordinates
      const x0 = xmin * canvas.width;
      const y0 = ymin * canvas.height;
      const x1 = xmax * canvas.width;
      const y1 = ymax * canvas.height;
      
      const width = x1 - x0;
      const height = y1 - y0;
      
      const scorePercent = round(score * 100, 1);
      const displayLabel = `${label} ${scorePercent}%`;
      const color = conf2color(score);

      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(x0, y0, width, height);
      
      // Draw label
      ctx.font = '20px Arial';
      ctx.fillStyle = color;
      ctx.fillText(displayLabel, x0, y0 - 5);

      // Draw semi-transparent fill
      ctx.fillStyle = color.replace(')', ', 0.2)').replace('rgb', 'rgba');
      ctx.fillRect(x0, y0, width, height);
    });
  };

  const runServerInference = async (ctx: CanvasRenderingContext2D) => {
    const result = await sendFrameToServer(ctx);
    if (result && result.detections) {
      drawDetections(ctx, result.detections);
    }
  };

  const runLiveDetection = async () => {
    if (liveDetection.current) {
      liveDetection.current = false;
      return;
    }
    liveDetection.current = true;
    while (liveDetection.current) {
      const startTime = Date.now();
      const ctx = capture();
      if (!ctx) return;
      await runServerInference(ctx);
      setTotalTime(Date.now() - startTime);
      await new Promise<void>((resolve) =>
        requestAnimationFrame(() => resolve())
      );
    }
  };

  const processImage = async () => {
    reset();
    const ctx = capture();
    if (!ctx) return;

    // create a copy of the canvas
    const boxCtx = document
      .createElement('canvas')
      .getContext('2d') as CanvasRenderingContext2D;
    boxCtx.canvas.width = ctx.canvas.width;
    boxCtx.canvas.height = ctx.canvas.height;
    boxCtx.drawImage(ctx.canvas, 0, 0);

    await runServerInference(boxCtx);
    ctx.drawImage(boxCtx.canvas, 0, 0, ctx.canvas.width, ctx.canvas.height);
  };

  const reset = async () => {
    var context = videoCanvasRef.current!.getContext('2d')!;
    context.clearRect(0, 0, originalSize.current[0], originalSize.current[1]);
    liveDetection.current = false;
  };

  if (SSR) {
    return <div>Loading...</div>;
  }

  return (
    <div className="flex flex-row flex-wrap w-full justify-evenly align-center">
      <div
        id="webcam-container"
        className="flex items-center justify-center webcam-container"
      >
        <Webcam
          mirrored={facingMode === 'user'}
          audio={false}
          ref={webcamRef}
          screenshotFormat="image/jpeg"
          imageSmoothing={true}
          videoConstraints={{
            facingMode: facingMode,
            // width: props.width,
            // height: props.height,
          }}
          onLoadedMetadata={() => {
            setWebcamCanvasOverlaySize();
            originalSize.current = [
              webcamRef.current!.video!.offsetWidth,
              webcamRef.current!.video!.offsetHeight,
            ] as number[];
          }}
          forceScreenshotSourceSize={true}
        />
        <canvas
          id="cv1"
          ref={videoCanvasRef}
          style={{
            position: 'absolute',
            zIndex: 10,
            backgroundColor: 'rgba(0,0,0,0)',
          }}
        ></canvas>
      </div>
      <div className="flex flex-col items-center justify-center">
        <div className="flex flex-row flex-wrap items-center justify-center gap-1 m-5">
          <div className="flex  items-center text-[10px] sm:text-1xl justify-center gap-1">
            <button
              onClick={async () => {
                const startTime = Date.now();
                await processImage();
                setTotalTime(Date.now() - startTime);
              }}
              className="p-2 border-2 border-dashed rounded-xl hover:translate-y-1 "
            >
              Capture Photo
            </button>
            <button
              onClick={async () => {
                if (liveDetection.current) {
                  liveDetection.current = false;
                } else {
                  runLiveDetection();
                }
              }}
              //on hover, shift the button up
              className={`
              p-2  border-dashed border-2 rounded-xl hover:translate-y-1 
              ${liveDetection.current ? 'bg-white text-black' : ''}
              
              `}
            >
              Live Detection
            </button>
          </div>
          <div className="flex  items-center text-[10px] sm:text-1xl justify-center gap-1">
            <button
              onClick={() => {
                reset();
                setFacingMode(facingMode === 'user' ? 'environment' : 'user');
              }}
              className="p-2 border-2 border-dashed rounded-xl hover:translate-y-1 "
            >
              Switch Camera
            </button>
            <button
              onClick={() => {
                reset();
                props.changeCurrentModelResolution();
              }}
              className="p-2 border-2 border-dashed rounded-xl hover:translate-y-1 "
            >
              Change Model
            </button>
            <button
              onClick={reset}
              className="p-2 border-2 border-dashed rounded-xl hover:translate-y-1 "
            >
              Reset
            </button>
          </div>
        </div>
        <div>Using {props.modelName}</div>
        <div className="flex flex-row flex-wrap items-center justify-between w-full gap-3 px-5">
          <div>
            {'Server Inference Time: ' + inferenceTime.toFixed() + 'ms'}
            <br />
            {'Network Latency: ' + networkLatency.toFixed() + 'ms'}
            <br />
            {'Total Time: ' + totalTime.toFixed() + 'ms'}
          </div>
          <div>
            <div>
              {'Server FPS: ' + (1000 / inferenceTime).toFixed(2) + 'fps'}
            </div>
            <div>{'Total FPS: ' + (1000 / totalTime).toFixed(2) + 'fps'}</div>
            <div>
              {'Network Overhead: +' + networkLatency.toFixed(2) + 'ms'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServerInferenceCamera;