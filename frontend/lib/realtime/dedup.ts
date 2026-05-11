/**
 * Bounded event ID deduplication set.
 * Prevents processing duplicate events on reconnect.
 */

const MAX_SIZE = 1000;

export class EventDedup {
  private seen = new Set<string>();
  private queue: string[] = [];

  /** Returns true if event_id is new (not a duplicate). */
  add(eventId: string): boolean {
    if (this.seen.has(eventId)) return false;
    this.seen.add(eventId);
    this.queue.push(eventId);
    if (this.queue.length > MAX_SIZE) {
      const evicted = this.queue.shift()!;
      this.seen.delete(evicted);
    }
    return true;
  }

  has(eventId: string): boolean {
    return this.seen.has(eventId);
  }

  get size(): number {
    return this.seen.size;
  }
}
