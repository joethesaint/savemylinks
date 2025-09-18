interface Frame {
    duration: number;
    imageMap: {
        source: string;
        x: number;
        y: number;
        width: number;
        height: number;
    };
    position: {
        x: number;
        y: number;
    };
}
interface Animation {
    frames: Frame[];
    useQueue: boolean;
}
interface AnimationMap {
    [key: string]: Animation;
}
export declare function getClippyAnimations(basePath: string): AnimationMap;
export {};
