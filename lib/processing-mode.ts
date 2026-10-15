// Browser inference remains a developer experiment, outside the normal setup flow.
let mode:'browser'|'companion'='companion';
export const processingMode=()=>mode;
export function selectProcessingMode(value:'browser'|'companion'){mode=value}
