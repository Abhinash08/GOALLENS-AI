import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faFutbol,
  faBullseye,
  faWandMagicSparkles,
} from "@fortawesome/free-solid-svg-icons";
import "./App.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function App() {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;

    const allowedExtensions = [
      "mp4",
      "avi",
      "mkv",
      "mov",
      "webm",
    ];

    const extension = selectedFile.name
      .split(".")
      .pop()
      .toLowerCase();

    if (!allowedExtensions.includes(extension)) {
      setError(
        "Please select an MP4, AVI, MKV, MOV, or WEBM video."
      );
      return;
    }

    setFile(selectedFile);
    setResult(null);
    setError("");
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragActive(false);

    const droppedFile = event.dataTransfer.files?.[0];

    if (droppedFile) {
      handleFile(droppedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a football video first.");
      return;
    }

    setProcessing(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      console.log("Uploading video:", file.name);

      const response = await fetch(
        `${API_BASE_URL}/api/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      console.log("====================================");
      console.log("GOALlens BACKEND RESPONSE");
      console.log("====================================");
      console.log(data);

      // Debug the possible goal fields
      console.log("GOAL DATA:", {
        goal_count: data.goal_count,
        goals_detected: data.goals_detected,
        goals: data.goals,
        scoreboard_goal_count:
          data.scoreboard?.goal_count,
        scoreboard_goals_detected:
          data.scoreboard?.goals_detected,
        scoreboard_goals:
          data.scoreboard?.goals,
        final_goal_windows:
          data.final_highlights?.goal_windows,
      });

      if (!response.ok) {
        throw new Error(
          data.detail || "Video processing failed."
        );
      }

      setResult(data);
    } catch (err) {
      console.error("UPLOAD ERROR:", err);

      setError(
        err.message ||
          "Could not connect to the GOALlens backend."
      );
    } finally {
      setProcessing(false);
    }
  };

  const formatTime = (seconds) => {
    if (
      seconds === null ||
      seconds === undefined ||
      Number.isNaN(Number(seconds))
    ) {
      return "N/A";
    }

    const totalSeconds = Math.round(Number(seconds));

    const minutes = Math.floor(totalSeconds / 60);
    const remainingSeconds = totalSeconds % 60;

    return `${minutes}:${String(
      remainingSeconds
    ).padStart(2, "0")}`;
  };

  const formatBytes = (bytes) => {
    if (!bytes) return "0 MB";

    return `${(
      Number(bytes) /
      (1024 * 1024)
    ).toFixed(2)} MB`;
  };

  const clearSelection = () => {
    setFile(null);
    setResult(null);
    setError("");
  };

  return (
    <div className="app">

      {/* =====================================================
          BACKGROUND
      ===================================================== */}

      <div className="background-grid"></div>
      <div className="background-glow glow-one"></div>
      <div className="background-glow glow-two"></div>


      {/* =====================================================
          NAVBAR
      ===================================================== */}

      <header className="navbar">

        <div className="brand">

          <div className="brand-mark">
            <FontAwesomeIcon icon={faFutbol} />
          </div>

          <div className="brand-text">
            <h1>
              GOAL<span className="brand-lens">lens</span>
            </h1>
          </div>

        </div>


        <div className="nav-center">

          <div className="nav-pill">
            <span className="live-dot"></span>
            FOOTBALL INTELLIGENCE SYSTEM
          </div>

        </div>


        <div className="nav-tech">

          <span>YOLO</span>

          <i></i>

          <span>OCR</span>

          <i></i>

          <span>KALMAN</span>

        </div>

      </header>


      {/* =====================================================
          MAIN
      ===================================================== */}

      <main className="main-container">

        {!result && (
          <>

            {/* =================================================
                HERO
            ================================================= */}

            <section className="hero">

              <div className="hero-eyebrow">

                <span className="eyebrow-line"></span>

                AI-POWERED FOOTBALL ANALYSIS

                <span className="eyebrow-line"></span>

              </div>


              <h2>

                Every match.

                <br />

                <span>Every moment.</span>

              </h2>


              <p>
                GOAL<span className="brand-lens-inline">lens</span> transforms full football
                matches into intelligent highlights using
                scoreboard OCR, ball detection, tracking
                and event analysis.
              </p>


              <div className="hero-features">

                <div className="hero-feature">
                  <FontAwesomeIcon icon={faFutbol} className="feature-icon" />
                  <span>Goal Detection</span>
                </div>

                <div className="hero-feature">
                  <FontAwesomeIcon icon={faBullseye} className="feature-icon" />
                  <span>Ball Tracking</span>
                </div>

                <div className="hero-feature">
                  <FontAwesomeIcon icon={faWandMagicSparkles} className="feature-icon" />
                  <span>AI Highlights</span>
                </div>

              </div>

            </section>


            {/* =================================================
                UPLOAD
            ================================================= */}

            <section className="upload-section">

              <div
                className={`upload-card ${
                  dragActive ? "drag-active" : ""
                } ${file ? "has-file" : ""}`}

                onDragOver={(event) => {
                  event.preventDefault();
                  setDragActive(true);
                }}

                onDragLeave={() =>
                  setDragActive(false)
                }

                onDrop={handleDrop}
              >

                {!file ? (

                  <>

                    <div className="upload-visual">

                      <div className="upload-orbit"></div>

                      <div className="upload-symbol">
                        ↑
                      </div>

                    </div>


                    <h3>
                      Drop your match here
                    </h3>


                    <p>
                      Upload a full football match
                      to generate AI highlights
                    </p>


                    <label className="browse-button">

                      Choose Video

                      <input
                        type="file"
                        accept=".mp4,.avi,.mkv,.mov,.webm,video/*"
                        hidden
                        onChange={(event) =>
                          handleFile(
                            event.target.files?.[0]
                          )
                        }
                      />

                    </label>


                    <div className="format-info">

                      <span>MP4</span>
                      <span>•</span>
                      <span>AVI</span>
                      <span>•</span>
                      <span>MKV</span>
                      <span>•</span>
                      <span>MOV</span>
                      <span>•</span>
                      <span>WEBM</span>

                    </div>

                  </>

                ) : (

                  <div className="selected-file">

                    <div className="file-icon">
                      🎬
                    </div>


                    <div className="file-details">

                      <span className="file-label">
                        SELECTED MATCH
                      </span>


                      <h3>
                        {file.name}
                      </h3>


                      <p>
                        {formatBytes(file.size)}
                      </p>

                    </div>


                    <button
                      className="remove-file"
                      onClick={clearSelection}
                      type="button"
                    >
                      ×
                    </button>

                  </div>

                )}

              </div>


              {/* ERROR */}

              {error && (

                <div className="error-message">

                  <span>!</span>

                  <div>

                    <strong>
                      Something went wrong
                    </strong>

                    <p>
                      {error}
                    </p>

                  </div>

                </div>

              )}


              {/* GENERATE BUTTON */}

              <button
                className="generate-button"
                disabled={!file || processing}
                onClick={handleUpload}
              >

                {processing ? (

                  <>

                    <span className="button-spinner"></span>

                    ANALYZING MATCH...

                  </>

                ) : (

                  <>

                    GENERATE AI HIGHLIGHTS

                    <span className="button-arrow">
                      →
                    </span>

                  </>

                )}

              </button>

            </section>


            {/* =================================================
                TECHNOLOGY
            ================================================= */}

            {!processing && (

              <section className="technology-section">

                <span>
                  POWERED BY
                </span>


                <div className="technology-list">

                  <div className="technology-item">
                    <span className="technology-dot"></span>
                    YOLO OBJECT DETECTION
                  </div>


                  <div className="technology-item">
                    <span className="technology-dot"></span>
                    SCOREBOARD OCR
                  </div>


                  <div className="technology-item">
                    <span className="technology-dot"></span>
                    KALMAN TRACKING
                  </div>


                  <div className="technology-item">
                    <span className="technology-dot"></span>
                    AI HIGHLIGHT SCORING
                  </div>

                </div>

              </section>

            )}


            {/* =================================================
                PROCESSING
            ================================================= */}

            {processing && (

              <section className="processing-panel">

                <div className="processing-top">

                  <div>

                    <span className="section-label">
                      PROCESSING MATCH
                    </span>


                    <h3>
                      GOALlens is analyzing the game
                    </h3>


                    <p>
                      This may take some time for
                      longer matches.
                    </p>

                  </div>


                  <div className="processing-ball">
                    ⚽
                  </div>

                </div>


                <div className="processing-steps">

                  <ProcessingStep
                    number="01"
                    title="Scoreboard"
                    description="Detecting score changes"
                  />

                  <ProcessingStep
                    number="02"
                    title="Ball Detection"
                    description="Finding the football"
                  />

                  <ProcessingStep
                    number="03"
                    title="Tracking"
                    description="Kalman trajectory"
                  />

                  <ProcessingStep
                    number="04"
                    title="Scoring"
                    description="Ranking moments"
                  />

                  <ProcessingStep
                    number="05"
                    title="Highlights"
                    description="Building final video"
                  />

                </div>

              </section>

            )}

          </>
        )}


        {/* =====================================================
            RESULTS
        ===================================================== */}

        {result && (

          <Results
            result={result}
            formatTime={formatTime}
            onReset={clearSelection}
          />

        )}

      </main>


      {/* =====================================================
          FOOTER
      ===================================================== */}

      <footer className="footer">

        <div className="footer-brand">

          <FontAwesomeIcon icon={faFutbol} className="footer-fa-icon" />

          <span>GOAL<span className="brand-lens">lens</span></span>

        </div>


        <span>
          Football Intelligence & Highlight Generation
        </span>


        <div className="footer-status">

          <span className="live-dot"></span>

          SYSTEM READY

        </div>

      </footer>

    </div>
  );
}


/* ============================================================
   PROCESSING STEP
   ============================================================ */

function ProcessingStep({
  number,
  title,
  description,
}) {
  return (

    <div className="processing-step">

      <span className="processing-number">
        {number}
      </span>


      <div className="processing-step-text">

        <strong>
          {title}
        </strong>

        <span>
          {description}
        </span>

      </div>


      <div className="processing-loader">

        <span></span>
        <span></span>
        <span></span>

      </div>

    </div>

  );
}


/* ============================================================
   RESULTS
   ============================================================ */

function Results({
  result,
  formatTime,
  onReset,
}) {

  const finalHighlights =
    result.final_highlights || {};

  const scoreboard =
    result.scoreboard || {};

  const ballDetection =
    result.ball_detection || {};

  const ballTracking =
    result.ball_tracking || {};

  const ballHighlights =
    result.ball_highlights || {};


  /* ==========================================================
     ROBUST VALUE MAPPING
     ========================================================== */

  /*
   * The backend terminal shows:
   *
   * Goals detected : 3
   *
   * Depending on the API response structure, the value
   * may be returned as:
   *
   * result.goal_count
   * result.goals_detected
   * result.goals
   * scoreboard.goal_count
   * scoreboard.goals_detected
   * scoreboard.goals
   *
   * We check all of them.
   */

  const goalCount =
    result.goal_count ??
    result.goals_detected ??
    result.goals ??
    scoreboard.goal_count ??
    scoreboard.goals_detected ??
    scoreboard.goals ??
    finalHighlights.goal_count ??
    finalHighlights.goals_detected ??
    finalHighlights.goal_windows ??
    0;


  const ballWindowCount =
    result.ball_windows ??
    ballHighlights.ball_windows ??
    ballHighlights.highlights ??
    finalHighlights.ball_windows ??
    0;


  const combinedWindowCount =
    result.combined_windows ??
    finalHighlights.combined_windows ??
    0;


  const finalWindowCount =
    result.final_windows ??
    finalHighlights.final_windows ??
    0;


  /*
   * Debug information.
   *
   * This will appear in the browser console and lets us
   * see exactly what the backend returned.
   */

  console.log("GOALlens RESULT DATA:", result);

  console.log("GOALlens GOAL COUNT:", goalCount);


  /* ==========================================================
     VIDEO URL
     ========================================================== */

  let videoUrl =
    finalHighlights.video_url || "";

  if (
    videoUrl &&
    !videoUrl.startsWith("http://") &&
    !videoUrl.startsWith("https://")
  ) {
    videoUrl =
      `${API_BASE_URL}${videoUrl}`;
  }


  return (

    <section className="results-page">


      {/* =====================================================
          RESULTS HEADER
      ===================================================== */}

      <div className="results-heading">

        <div>

          <div className="success-badge">

            <span>✓</span>

            PROCESSING COMPLETE

          </div>


          <h2>

            Your match.

            <br />

            <span>Reimagined.</span>

          </h2>


          <p>

            Match ID:{" "}

            <strong>
              {result.match_id || "N/A"}
            </strong>

          </p>

        </div>


        <button
          className="new-match-button"
          onClick={onReset}
          type="button"
        >

          <span>+</span>

          New Match

        </button>

      </div>


      {/* =====================================================
          FINAL VIDEO
      ===================================================== */}

      {videoUrl && (

        <div className="video-container">

          <div className="video-header">

            <div>

              <span className="video-label">
                FINAL AI HIGHLIGHTS
              </span>


              <strong>
                GOALlens Generated Highlight Reel
              </strong>

            </div>


            <span className="video-ready">
              ● READY
            </span>

          </div>


          <video
            controls
            className="highlight-video"
            src={videoUrl}
            preload="metadata"
          >
            Your browser does not support video
            playback.
          </video>


          <div className="video-footer">

            <span>
              AI generated highlight video
            </span>


            <a
              href={videoUrl}
              target="_blank"
              rel="noreferrer"
              className="open-video"
            >
              Open full video →
            </a>

          </div>

        </div>

      )}


      {!videoUrl && (

        <div className="error-message">

          <span>!</span>

          <div>

            <strong>
              Final video unavailable
            </strong>

            <p>
              Processing completed but no final
              video URL was returned.
            </p>

          </div>

        </div>

      )}


      {/* =====================================================
          MAIN STATISTICS
      ===================================================== */}

      <section className="results-stats">

        <div className="stats-grid">


          {/* GOALS */}

          <StatCard
            icon="⚽"
            title="Goals"
            value={goalCount}
            label="Detected goals"
            accent
          />


          {/* BALL DETECTIONS */}

          <StatCard
            icon="🎯"
            title="Ball Detections"
            value={
              ballDetection.detection_rows ?? 0
            }
            label="Detection rows"
          />


          {/* TRACKING */}

          <StatCard
            icon="📍"
            title="Tracking Coverage"
            value={
              ballTracking.coverage !== undefined &&
              ballTracking.coverage !== null
                ? `${Number(
                    ballTracking.coverage
                  ).toFixed(1)}%`
                : "N/A"
            }
            label="Valid tracking"
          />


          {/* HIGHLIGHTS */}

          <StatCard
            icon="⭐"
            title="Highlights"
            value={
              ballHighlights.highlights ??
              ballHighlights.ball_windows ??
              0
            }
            label="Highlight windows"
            accent
          />

        </div>

      </section>


      {/* =====================================================
          ANALYSIS GRID
      ===================================================== */}

      <section className="analysis-grid">


        {/* SCOREBOARD */}

        <AnalysisCard
          icon="⚽"
          title="Scoreboard Analysis"
          subtitle="Goal detection & OCR"
        >

          <AnalysisRow
            label="Goals detected"
            value={goalCount}
            highlight
          />


          <AnalysisRow
            label="Processing time"
            value={`${Number(
              scoreboard.processing_time || 0
            ).toFixed(2)}s`}
          />


          <AnalysisRow
            label="Goal events"
            value={
              scoreboard.goal_events_csv
                ? "Available"
                : "N/A"
            }
          />

        </AnalysisCard>


        {/* BALL DETECTION */}

        <AnalysisCard
          icon="🎯"
          title="Ball Detection"
          subtitle="YOLO object detection"
        >

          <AnalysisRow
            label="Frames processed"
            value={
              ballDetection.frames_processed ??
              "N/A"
            }
          />


          <AnalysisRow
            label="Detection rows"
            value={
              ballDetection.detection_rows ??
              "N/A"
            }
          />


          <AnalysisRow
            label="Processing time"
            value={`${Number(
              ballDetection.processing_time || 0
            ).toFixed(2)}s`}
          />

        </AnalysisCard>


        {/* BALL TRACKING */}

        <AnalysisCard
          icon="📍"
          title="Ball Tracking"
          subtitle="Interpolation + Kalman filter"
        >

          <AnalysisRow
            label="Detected"
            value={
              ballTracking.detected ??
              "N/A"
            }
          />


          <AnalysisRow
            label="Kalman predictions"
            value={
              ballTracking.kalman ??
              "N/A"
            }
          />


          <AnalysisRow
            label="Lost frames"
            value={
              ballTracking.lost ??
              "N/A"
            }
          />


          <AnalysisRow
            label="Coverage"
            value={
              ballTracking.coverage !== undefined &&
              ballTracking.coverage !== null
                ? `${Number(
                    ballTracking.coverage
                  ).toFixed(2)}%`
                : "N/A"
            }
            highlight
          />

        </AnalysisCard>


        {/* HIGHLIGHT SCORING */}

        <AnalysisCard
          icon="⭐"
          title="Highlight Scoring"
          subtitle="AI moment analysis"
        >

          <AnalysisRow
            label="Highlight windows"
            value={
              ballHighlights.highlights ??
              ballHighlights.ball_windows ??
              0
            }
            highlight
          />


          <AnalysisRow
            label="Highlight duration"
            value={formatTime(
              ballHighlights.duration_seconds
            )}
          />


          <AnalysisRow
            label="Processing time"
            value={`${Number(
              ballHighlights.processing_time || 0
            ).toFixed(2)}s`}
          />

        </AnalysisCard>

      </section>


      {/* =====================================================
          FINAL SUMMARY
      ===================================================== */}

      <section className="summary-section">

        <div className="summary-heading">

          <div>

            <span className="section-label">
              FINAL OUTPUT
            </span>


            <h3>
              Highlight Summary
            </h3>

          </div>


          <span className="match-id">
            {result.match_id || "MATCH"}
          </span>

        </div>


        <div className="summary-grid">


          <SummaryStat
            icon="⚽"
            label="Goal Windows"
            value={
              finalHighlights.goal_windows ??
              goalCount
            }
          />


          <SummaryStat
            icon="🎯"
            label="Ball Windows"
            value={
              finalHighlights.ball_windows ??
              ballWindowCount
            }
          />


          <SummaryStat
            icon="🔗"
            label="Combined Windows"
            value={
              finalHighlights.combined_windows ??
              combinedWindowCount
            }
          />


          <SummaryStat
            icon="✨"
            label="Final Windows"
            value={
              finalHighlights.final_windows ??
              finalWindowCount
            }
          />


          <SummaryStat
            icon="⏱"
            label="Highlight Duration"
            value={formatTime(
              finalHighlights.duration_seconds
            )}
          />


          <SummaryStat
            icon="⚡"
            label="Total Processing"
            value={`${Number(
              result.processing_time || 0
            ).toFixed(1)}s`}
          />

        </div>

      </section>


      {/* =====================================================
          PIPELINE
      ===================================================== */}

      <section className="pipeline-summary">

        <span className="section-label">
          ANALYSIS PIPELINE
        </span>


        <div className="pipeline-line">

          <PipelineBadge
            number="01"
            text="OCR"
          />

          <div className="pipeline-connector"></div>


          <PipelineBadge
            number="02"
            text="YOLO"
          />

          <div className="pipeline-connector"></div>


          <PipelineBadge
            number="03"
            text="KALMAN"
          />

          <div className="pipeline-connector"></div>


          <PipelineBadge
            number="04"
            text="SCORING"
          />

          <div className="pipeline-connector"></div>


          <PipelineBadge
            number="05"
            text="HIGHLIGHTS"
          />

        </div>

      </section>

    </section>

  );
}


/* ============================================================
   STAT CARD
   ============================================================ */

function StatCard({
  icon,
  title,
  value,
  label,
  accent = false,
}) {

  return (

    <div
      className={`stat-card ${
        accent ? "stat-accent" : ""
      }`}
    >

      <div className="stat-icon">
        {icon}
      </div>


      <div className="stat-content">

        <span className="stat-title">
          {title}
        </span>


        <strong className="stat-value">
          {value}
        </strong>


        <small className="stat-label">
          {label}
        </small>

      </div>

    </div>

  );
}


/* ============================================================
   ANALYSIS CARD
   ============================================================ */

function AnalysisCard({
  icon,
  title,
  subtitle,
  children,
}) {

  return (

    <div className="analysis-card">

      <div className="analysis-header">

        <div className="analysis-icon">
          {icon}
        </div>


        <div>

          <h3>
            {title}
          </h3>


          <span>
            {subtitle}
          </span>

        </div>

      </div>


      <div className="analysis-content">
        {children}
      </div>

    </div>

  );
}


/* ============================================================
   ANALYSIS ROW
   ============================================================ */

function AnalysisRow({
  label,
  value,
  highlight = false,
}) {

  return (

    <div
      className={`analysis-row ${
        highlight
          ? "row-highlight"
          : ""
      }`}
    >

      <span>
        {label}
      </span>


      <strong>
        {value}
      </strong>

    </div>

  );
}


/* ============================================================
   SUMMARY STAT
   ============================================================ */

function SummaryStat({
  icon,
  label,
  value,
}) {

  return (

    <div className="summary-stat">

      <span className="summary-icon">
        {icon}
      </span>


      <div>

        <span>
          {label}
        </span>


        <strong>
          {value}
        </strong>

      </div>

    </div>

  );
}


/* ============================================================
   PIPELINE BADGE
   ============================================================ */

function PipelineBadge({
  number,
  text,
}) {

  return (

    <div className="pipeline-badge">

      <span>
        {number}
      </span>


      <strong>
        {text}
      </strong>

    </div>

  );
}


export default App;