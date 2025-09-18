import { ModernClippy } from './agent';

export * from './agent';
export * from './types';
export * from './loader';
export interface ClippyOptions {
    basePath: string;
}
export declare function initClippy(options?: ClippyOptions): Promise<ModernClippy>;
