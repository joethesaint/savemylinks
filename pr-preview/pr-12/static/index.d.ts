import { ModernClippy } from './agent';

export * from './agent';
export interface ClippyOptions {
    /** Folder that holds agents/Clippy/ (default "/static/") */
    basePath?: string;
    /** Show right away unless the person hid it before (default true) */
    show?: boolean;
}
export declare function initClippy(options?: ClippyOptions): Promise<ModernClippy>;
export declare function loadAgent(basePath?: string, name?: string): Promise<ModernClippy>;
export declare const assistantPrefs: { get(): Record<string, unknown>; set(patch: Record<string, unknown>): Record<string, unknown> };
