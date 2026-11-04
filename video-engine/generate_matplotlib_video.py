#!/usr/bin/env python3
"""
PrimeEdge TikTok Video Generator
Matplotlib + FFmpeg Pipeline
Template A: One chart, one question
Constitution: PRIMEEDGE_TIKTOP_CONSTITUTION.md
"""

import matplotlib.pyplot as plt
import numpy as np
import subprocess
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────
OUTPUT_DIR = Path("video-engine/out")
FRAMES_DIR = Path("video-engine/frames")
OUTPUT_VIDEO = OUTPUT_DIR / "TemplateA_RegimeQuestion.mp4"

# Video settings
FPS = 30
DURATION = 30  # Template A: 15-35 seconds
TOTAL_FRAMES = FPS * DURATION
WIDTH = 1080
HEIGHT = 1920  # 9:16 vertical

# Optimize: Use smaller DPI for faster rendering
DPI = 72

# Style settings
plt.style.use('dark_background')
BG_COLOR = '#0f172a'
TEXT_COLOR = '#ffffff'
ACCENT_BLUE = '#3b82f6'
ACCENT_YELLOW = '#eab308'
ACCENT_RED = '#ef4444'
ACCENT_GREEN = '#22c55e'

# ── Data Generation (Simulated DXY regimes) ────────────────────
def generate_regime_data():
    """Generate simulated price data for two regimes"""
    np.random.seed(42)
    t = np.linspace(0, 100, 200)
    price_bearish = 100 + np.cumsum(np.random.normal(0.5, 2, 200))
    price_bullish = 100 + np.cumsum(np.random.normal(-0.3, 2, 200))
    return t, price_bearish, price_bullish

# ── Frame Generation ───────────────────────────────────────────
def create_frame(frame_num, t, price_bearish, price_bullish):
    """Create a single frame for the video"""
    fig = plt.figure(figsize=(WIDTH/100, HEIGHT/100), dpi=DPI, facecolor=BG_COLOR)
    ax = fig.add_subplot(111, facecolor=BG_COLOR)
    
    # Template A: One chart, one question (15-35s)
    # Sequence: chart/question in frame one → highlight level → explanation → trigger/invalidation → CTA
    
    # Scene 1: Hook (0-90 frames = 0-3s) - Chart/question in frame one
    if frame_num < 90:
        # Chart visible immediately with question
        ax_bearish = fig.add_axes([0.1, 0.55, 0.8, 0.35], facecolor='#1e293b')
        ax_bearish.plot(t, price_bearish, color=ACCENT_GREEN, linewidth=3)
        ax_bearish.set_title("Bearish DXY Regime", color=ACCENT_GREEN, fontsize=28, fontweight='bold')
        ax_bearish.tick_params(colors=TEXT_COLOR, labelsize=16)
        ax_bearish.grid(True, alpha=0.2, color=TEXT_COLOR)
        
        ax.text(0.5, 0.12, "Same ticker, two timeframes,", ha='center', va='center',
                fontsize=36, fontweight='bold', color=TEXT_COLOR, transform=ax.transAxes)
        ax.text(0.5, 0.06, "opposite signals—why?", ha='center', va='center',
                fontsize=36, fontweight='bold', color=ACCENT_YELLOW, transform=ax.transAxes)
        
        # Source/date label
        ax.text(0.05, 0.95, "XAUUSD • H4 • 2020-2026 • REPLAY", ha='left', va='top',
                fontsize=16, color='#94a3b8', transform=ax.transAxes)
    
    # Scene 2: Highlight the level (90-270 frames = 3-9s)
    elif frame_num < 270:
        progress = (frame_num - 90) / 180
        
        ax_bearish = fig.add_axes([0.1, 0.55, 0.8, 0.35], facecolor='#1e293b')
        ax_bearish.plot(t, price_bearish, color=ACCENT_GREEN, linewidth=3)
        ax_bearish.set_title("Bearish DXY Regime", color=ACCENT_GREEN, fontsize=28, fontweight='bold')
        ax_bearish.tick_params(colors=TEXT_COLOR, labelsize=16)
        ax_bearish.grid(True, alpha=0.2, color=TEXT_COLOR)
        
        # Highlight key level progressively
        if progress > 0.5:
            ax_bearish.axhline(y=105, color=ACCENT_YELLOW, linewidth=4, linestyle='--')
            ax.text(0.1, 0.45, "Key resistance level", ha='left', va='center',
                    fontsize=24, color=ACCENT_YELLOW, transform=ax.transAxes)
        
        ax.text(0.5, 0.12, "This level marks regime entry", ha='center', va='center',
                fontsize=32, fontweight='bold', color=TEXT_COLOR, transform=ax.transAxes)
        
        ax.text(0.05, 0.95, "XAUUSD • H4 • 2020-2026 • REPLAY", ha='left', va='top',
                fontsize=16, color='#94a3b8', transform=ax.transAxes)
    
    # Scene 3: Explanation (270-450 frames = 9-15s) - Competing interpretation
    elif frame_num < 450:
        ax_bullish = fig.add_axes([0.1, 0.55, 0.8, 0.35], facecolor='#1e293b')
        ax_bullish.plot(t, price_bullish, color=ACCENT_RED, linewidth=3)
        ax_bullish.set_title("Bullish DXY Regime", color=ACCENT_RED, fontsize=28, fontweight='bold')
        ax_bullish.tick_params(colors=TEXT_COLOR, labelsize=16)
        ax_bullish.grid(True, alpha=0.2, color=TEXT_COLOR)
        
        ax.text(0.5, 0.35, "Bearish DXY: 69% win rate", ha='center', va='center',
                fontsize=40, fontweight='bold', color=ACCENT_GREEN, transform=ax.transAxes)
        ax.text(0.5, 0.25, "Bullish DXY: 30% win rate", ha='center', va='center',
                fontsize=40, fontweight='bold', color=ACCENT_RED, transform=ax.transAxes)
        
        ax.text(0.5, 0.12, "Same setup, opposite outcomes", ha='center', va='center',
                fontsize=28, fontweight='bold', color=TEXT_COLOR, transform=ax.transAxes)
        
        ax.text(0.05, 0.95, "XAUUSD • H4 • 2020-2026 • REPLAY", ha='left', va='top',
                fontsize=16, color='#94a3b8', transform=ax.transAxes)
    
    # Scene 4: Trigger and invalidation (450-630 frames = 15-21s)
    elif frame_num < 630:
        ax.text(0.5, 0.6, "Trigger: DXY in BEARISH regime", ha='center', va='center',
                fontsize=36, fontweight='bold', color=ACCENT_GREEN, transform=ax.transAxes)
        ax.text(0.5, 0.5, "Invalidation: DXY crosses BULLISH", ha='center', va='center',
                fontsize=36, fontweight='bold', color=ACCENT_RED, transform=ax.transAxes)
        
        ax.text(0.5, 0.3, "Check DXY before entry", ha='center', va='center',
                fontsize=32, fontweight='bold', color=ACCENT_YELLOW, transform=ax.transAxes)
        
        ax.text(0.05, 0.95, "XAUUSD • H4 • 2020-2026 • REPLAY", ha='left', va='top',
                fontsize=16, color='#94a3b8', transform=ax.transAxes)
    
    # Scene 5: CTA (630-900 frames = 21-30s) - Saveable checklist
    else:
        ax.text(0.5, 0.55, "PRIMEEDGE.APP", ha='center', va='center',
                fontsize=70, fontweight='bold', color=ACCENT_BLUE, transform=ax.transAxes)
        
        ax.text(0.5, 0.4, "Save the regime checklist", ha='center', va='center',
                fontsize=40, fontweight='bold', color=TEXT_COLOR, transform=ax.transAxes)
        
        ax.text(0.5, 0.25, "Evidence before execution.", ha='center', va='center',
                fontsize=28, fontweight='bold', color='#94a3b8', transform=ax.transAxes)
        
        # Disclaimer
        ax.text(0.5, 0.05, "Historical analysis is not a guarantee of future results. Trading involves risk.",
                ha='center', va='center', fontsize=14, color='#64748b', transform=ax.transAxes)
    
    ax.set_axis_off()
    
    frame_path = FRAMES_DIR / f"frame_{frame_num:04d}.png"
    plt.savefig(frame_path, dpi=100, bbox_inches='tight', pad_inches=0.1, facecolor=BG_COLOR)
    plt.close(fig)
    return frame_path

# ── Main Generation ─────────────────────────────────────────────
def main():
    print("Generating PrimeEdge TikTok video (Matplotlib + FFmpeg)")
    print("Template A: One chart, one question")
    print("=" * 60)
    
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("1. Generating regime data...")
    t, price_bearish, price_bullish = generate_regime_data()
    
    print(f"2. Generating {TOTAL_FRAMES} frames...")
    for frame_num in range(TOTAL_FRAMES):
        create_frame(frame_num, t, price_bearish, price_bullish)
        if (frame_num + 1) % 100 == 0:
            print(f"   {frame_num + 1}/{TOTAL_FRAMES} frames generated")
    
    print(f"[OK] {TOTAL_FRAMES} frames generated")
    
    print("3. Encoding video with FFmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "frame_%04d.png"),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(OUTPUT_VIDEO)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"[OK] Video saved to: {OUTPUT_VIDEO}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] FFmpeg error: {e}")
        return
    
    # Cleanup frames
    print("4. Cleaning up frames...")
    for f in FRAMES_DIR.glob("*.png"):
        f.unlink()
    FRAMES_DIR.rmdir()
    
    print("=" * 60)
    print("[OK] Video generation complete!")
    print(f"Duration: {DURATION}s @ {FPS}fps | Size: {WIDTH}x{HEIGHT}")

if __name__ == "__main__":
    main()
