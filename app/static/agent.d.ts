export interface PlayOptions { /** ms before the animation is asked to leave by its exit branch (default 5000) */ timeout?: number; }
export interface SpeakOptions { /** ms the bubble stays; 0 keeps it until clicked (default 5000) */ duration?: number; tone?: '' | 'saved' | 'duplicate' | 'invalid'; }

export declare class ModernClippy {
    container: HTMLElement;
    visible: boolean;
    readonly animations: string[];
    hasAnimation(name: string): boolean;
    show(): void;
    hide(): void;
    /** Hides with the Hide animation and remembers the choice in this browser. */
    dismiss(): void;
    /** Resolves true when the animation finished, false if it was unknown, replaced or stopped. */
    play(animationName: string, options?: PlayOptions): Promise<boolean>;
    stop(): void;
    startIdle(minMs?: number, maxMs?: number): void;
    stopIdle(): void;
    speak(text: string, options?: SpeakOptions): void;
    closeBubble(): void;
}
