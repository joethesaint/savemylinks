export interface AnimationData {
    frames: Frame[];
    useQueue: boolean;
}
export interface Frame {
    duration: number;
    imageMap: ImageMap;
    position: Position;
    sound?: string;
}
export interface ImageMap {
    source: string;
    x: number;
    y: number;
    width: number;
    height: number;
}
export interface Position {
    x: number;
    y: number;
}
export interface AgentData {
    overlayCount: number;
    sounds: string[];
    framesize: [number, number];
    animations: Record<string, AnimationData>;
    sizes: [number, number][];
}
