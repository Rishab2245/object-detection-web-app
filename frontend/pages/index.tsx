import Head from "next/head";
import Yolo from "../components/models/Yolo";
import { useEffect, useState } from "react";
import { QRCodeSVG } from 'qrcode.react';
import styles from '../styles/Home.module.css';

const Home = () => {
  const [currentUrl, setCurrentUrl] = useState('');

  useEffect(() => {
    setCurrentUrl(window.location.href);
  }, []);

  return (
    <>
      <Head>
        <title>AI Vision - Real-Time Object Detection</title>
        <meta name="description" content="Clean AI-powered real-time object detection application" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <main className={styles.main}>
        {/* Hero Section */}
        <div className={styles.title}>
          <h1>AI Vision</h1>
          <p>Real-Time Object Detection</p>
        </div>

        {/* Main Content Card */}
        <div className={styles.contentCard}>
          <div className={styles.modelContainer}>
            <Yolo />
          </div>
        </div>

        {/* QR Code Section */}
        {currentUrl && (
          <div className={styles.qrSection}>
            <h2>Share</h2>
            <div className={styles.qrCode}>
              <QRCodeSVG 
                value={currentUrl} 
                size={160} 
                level="H"
                fgColor="black"
                bgColor="transparent"
              />
            </div>
            <p className={styles.qrUrl}>{currentUrl}</p>
          </div>
        )}

        {/* Footer */}
        <div className={styles.footer}>
          <p>
            Created by{" "}
            <a
              href="https://portfolio-g7en.vercel.app/"
              target="_blank"
              rel="noopener noreferrer"
            >
              @Rishab chaudhary
            </a>
          </p>
        </div>
      </main>
    </>
  );
};

export default Home;