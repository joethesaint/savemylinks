import { AgentData } from './types';

export declare class ModernClippy {
    private element;
    container: HTMLElement;
    private currentAnimation?;
    private queue;
    private data;
    private overlay;
    constructor(agentData: AgentData);
    private setupDOM;
    show(): void;
    hide(): void;
    play(animationName: string): Promise<void>;
    private playAnimation;
    private renderFrame;
    speak(text: string, duration?: number): void;
    moveTo(x: number, y: number, duration?: number): void;
}
