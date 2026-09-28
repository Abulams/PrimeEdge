// NotificationService.ts
// Handles synthesized audio alerts and browser desktop push notifications

class NotificationService {
  private audioCtx: AudioContext | null = null;
  private notifiedSet: Set<string> = new Set();
  private soundEnabled: boolean = true;
  private pushEnabled: boolean = true;

  constructor() {
    // Load stored preferences
    const soundPref = localStorage.getItem('marketos_sound_enabled');
    const pushPref = localStorage.getItem('marketos_push_enabled');
    if (soundPref !== null) this.soundEnabled = soundPref === 'true';
    if (pushPref !== null) this.pushEnabled = pushPref === 'true';
  }

  public isSoundEnabled(): boolean {
    return this.soundEnabled;
  }

  public setSoundEnabled(enabled: boolean) {
    this.soundEnabled = enabled;
    localStorage.setItem('marketos_sound_enabled', String(enabled));
  }

  public isPushEnabled(): boolean {
    return this.pushEnabled;
  }

  public setPushEnabled(enabled: boolean) {
    this.pushEnabled = enabled;
    localStorage.setItem('marketos_push_enabled', String(enabled));
  }

  public async requestPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
      return 'denied';
    }
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      this.setPushEnabled(true);
    }
    return permission;
  }

  public playReadyChime() {
    if (!this.soundEnabled) return;
    try {
      if (!this.audioCtx) {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioContextClass) {
          this.audioCtx = new AudioContextClass();
        }
      }

      if (!this.audioCtx) return;

      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }

      const now = this.audioCtx.currentTime;

      // Two-tone institutional chime (E5 -> B5)
      const osc1 = this.audioCtx.createOscillator();
      const osc2 = this.audioCtx.createOscillator();
      const gain1 = this.audioCtx.createGain();
      const gain2 = this.audioCtx.createGain();

      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(659.25, now); // E5
      gain1.gain.setValueAtTime(0.15, now);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

      osc2.type = 'triangle';
      osc2.frequency.setValueAtTime(987.77, now + 0.12); // B5
      gain2.gain.setValueAtTime(0.001, now);
      gain2.gain.setValueAtTime(0.2, now + 0.12);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.6);

      osc1.connect(gain1);
      gain1.connect(this.audioCtx.destination);
      osc2.connect(gain2);
      gain2.connect(this.audioCtx.destination);

      osc1.start(now);
      osc1.stop(now + 0.35);
      osc2.start(now + 0.12);
      osc2.stop(now + 0.6);
    } catch (e) {
      console.warn('Audio chime error:', e);
    }
  }

  public notifyReadyCard(
    instrument: string,
    direction: string,
    winRate: number,
    whyThisNow?: string,
    onClickCallback?: () => void
  ) {
    const key = `${instrument}-${direction}-${Math.floor(Date.now() / (1000 * 60 * 15))}`; // 15-min debounce key
    if (this.notifiedSet.has(key)) {
      return; // Avoid repeat notification within 15 minutes
    }
    this.notifiedSet.add(key);

    // 1. Play Audio Chime
    this.playReadyChime();

    // 2. Dispatch Desktop Push Notification
    if (this.pushEnabled && 'Notification' in window && Notification.permission === 'granted') {
      try {
        const title = `🚨 Market OS Alert: ${instrument} ${direction} is READY!`;
        const body = `Win Probability: ${Math.round(winRate * 100)}% | ${whyThisNow || 'T0 Inception Corridor reached. Click to review setup.'}`;
        
        const notif = new Notification(title, {
          body,
          icon: '/favicon.png',
          badge: '/favicon.png',
          tag: `ready-${instrument}`,
          requireInteraction: true,
        });

        notif.onclick = () => {
          window.focus();
          notif.close();
          if (onClickCallback) onClickCallback();
        };
      } catch (e) {
        console.warn('Desktop notification dispatch error:', e);
      }
    }
  }

  public testAlert(onClickCallback?: () => void) {
    this.playReadyChime();
    if ('Notification' in window) {
      if (Notification.permission === 'granted') {
        const notif = new Notification('🔔 Market OS Alert Test', {
          body: 'Audio chime and desktop push notifications are active and ready!',
          icon: '/favicon.png',
          tag: 'test-alert'
        });
        notif.onclick = () => {
          window.focus();
          notif.close();
          if (onClickCallback) onClickCallback();
        };
      } else {
        this.requestPermission();
      }
    }
  }
}

export const notificationService = new NotificationService();
