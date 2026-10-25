import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";
import { createDurabilityState } from "/plugins/durable_execution/webui/durability-state.js";

import { toastFrontendError, toastFrontendInfo } from "/components/notifications/notification-store.js";

export const store = createStore("durabilityStore", createDurabilityState(
  (payload) => callJsonApi("/plugins/durable_execution/durability", payload),
  () => crypto.randomUUID(),
  (kind, message) => (kind === "error" ? toastFrontendError : toastFrontendInfo)(message, "Durable Execution"),
));
