import React from 'react';

// Assuming you are using CSS Modules, import the styles.
// The CSS for this component should be added to your Home.module.css file.
import styles from '../styles/Home.module.css';

interface ModeToggleProps {
  mode: 'wasm' | 'server';
  onModeChange: (mode: 'wasm' | 'server') => void;
  disabled?: boolean;
}

const ModeToggle = ({ mode, onModeChange, disabled = false }: ModeToggleProps) => {
  const isServerMode = mode === 'server';

  return (
    <div className={styles.modeToggleContainer}>
      <label htmlFor="modeToggle" className={styles.modeToggleLabel}>
        Inference Mode
      </label>
      <div className={styles.toggleSwitch}>
        <input
          type="checkbox"
          id="modeToggle"
          checked={isServerMode}
          onChange={(e) => onModeChange(e.target.checked ? 'server' : 'wasm')}
          disabled={disabled}
          className={styles.toggleInput}
        />
        <label htmlFor="modeToggle" className={styles.toggleLabel}>
          <span className={styles.toggleSlider}></span>
          {!isServerMode && (
            <span className={`${styles.toggleText} ${styles.wasmText}`}>WASM</span>
          )}
          {isServerMode && (
            <span className={`${styles.toggleText} ${styles.serverText}`}>Server</span>
          )}
        </label>
      </div>
      <p className={styles.modeDescription}>
        {isServerMode
          ? 'Running inference on a remote server.'
          : 'Running inference locally in your browser.'}
      </p>
    </div>
  );
};

export default ModeToggle; 