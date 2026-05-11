/**
 * Exponential backoff reconnect strategy.
 */

export interface ReconnectConfig {
  initialDelayMs: number;
  maxDelayMs: number;
  factor: number;
  maxAttempts: number;
}

export const DEFAULT_RECONNECT_CONFIG: ReconnectConfig = {
  initialDelayMs: 500,
  maxDelayMs: 30_000,
  factor: 2,
  maxAttempts: 10,
};

export class ReconnectStrategy {
  private attempt = 0;
  private readonly config: ReconnectConfig;

  constructor(config: ReconnectConfig = DEFAULT_RECONNECT_CONFIG) {
    this.config = config;
  }

  /** Returns delay in ms for current attempt, or null if max attempts exceeded. */
  nextDelay(): number | null {
    if (this.attempt >= this.config.maxAttempts) return null;
    const delay = Math.min(
      this.config.initialDelayMs * Math.pow(this.config.factor, this.attempt),
      this.config.maxDelayMs,
    );
    this.attempt++;
    return delay;
  }

  reset(): void {
    this.attempt = 0;
  }

  get attemptCount(): number {
    return this.attempt;
  }
}
