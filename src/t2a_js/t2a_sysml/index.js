/**
 * T2A-ESS slot model -> EFFBD SysML converter (JS port of src/t2a_sysml).
 */
export { T2AModel, loadModel, loadModelFromObject, slotId, SLOT_COLLECTIONS, ALL_SLOT_COLLECTIONS } from "./model.js";
export { convertModel, convertFile, CONVERTER_VERSION } from "./converter.js";
export { convertStateModel, convertStateFile, stateSummary, stateGraph, STATE_CONVERTER_VERSION } from "./state_converter.js";
export { renderStateSvg, renderStateHtml } from "./state_diagram.js";
export { validateEffbd, validateSchema, summarize, RELATION_CONTRACT, REGISTERED_CUSTOM_TYPES } from "./validate.js";
