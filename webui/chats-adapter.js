import { callJsonApi } from "/js/api.js";
import { sendJsonData, getContext, toastFetchError, justToast } from "/index.js";
import { store as chatsStore } from "/components/sidebar/chats/chats-store.js";

const changes = {
 resetRequests: {}, removalRequests: {},
  async killChat(id) {
    if (!id) {
      console.error("No chat ID provided for deletion");
      return;
    }
    if (this.deletedContextIds[id]) return;

    const removedContext = this.contexts.find((context) => context.id === id);
    const deletingSelectedContext = this.selected === id || getContext() === id;

    // Remove first, before selecting the fallback chat. Alpine batches both
    // state changes into one render so the old row cannot remain above the new
    // selection while the HTTP request is in flight.
    this.deletedContextIds = { ...this.deletedContextIds, [id]: true };
    this.contexts = this.contexts.filter((context) => context.id !== id);

    try {
      // Switch to another context if deleting current
      if (deletingSelectedContext) {
        await this.switchFromContext(id);
      }

      let payload = this.removalRequests[id];
      if (!payload) {
        const scope = await callJsonApi("/plugins/durable_execution/durability", {action: "context_metadata", context: id});
        payload = scope.shared ? {context: id, request_id: crypto.randomUUID(), run_id: scope.run_id,
          expected_generation: scope.generation, epoch: scope.epoch, version: scope.version} : {context: id};
        this.removalRequests[id] = payload;
      }
      let result = await callJsonApi("/chat_remove", payload);
      for (let attempt = 0; result.queued && attempt < 20; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 250));
        result = await callJsonApi("/plugins/durable_execution/durability", {action: "command_status", context: id,
          run_id: payload.run_id, request_id: payload.request_id});
        if (!["pending", "applied", "rejected"].includes(result.command?.state)) {
          throw new Error("Chat removal receipt is unavailable. Retry to check the original request.");
        }
        result.queued = result.command?.state === "pending";
      }
      if (result.queued) {
        const waiting = new Error("Chat removal is queued. It will finish when a compatible worker is available.");
        waiting.removalPending = true;
        throw waiting;
      }
      if (result.command?.state === "rejected") {
        delete this.removalRequests[id];
        throw new Error(result.command.error || "The worker rejected this removal. Refresh the chat before trying again.");
      }
      delete this.removalRequests[id];
      const unresolved = result.command?.unresolved_provider_calls || 0;
      justToast(unresolved ? `Chat removed; ${unresolved} provider request(s) had no returned identifier.` :
        "Chat deleted successfully", unresolved ? "info" : "success", 2500, "chat-removal");
    } catch (e) {
      const deletedContextIds = { ...this.deletedContextIds };
      delete deletedContextIds[id];
      this.deletedContextIds = deletedContextIds;

      // Roll back the optimistic row removal without disturbing any chat the
      // user selected while the request was pending.
      if (removedContext && !this.contexts.some((context) => context.id === id)) {
        this.contexts = [...this.contexts, removedContext].sort(
          (a, b) => (b.created_at || 0) - (a.created_at || 0),
        );
      }

      if (e.removalPending) justToast(e.message, "info", 4000, "chat-removal");
      else {
        console.error("Error deleting chat:", e);
        toastFetchError("Error deleting chat", e);
      }
    }
  },
  async resetChat(ctxid = null) {
    try {
      const context = ctxid || this.selected || getContext();
      const requestId = this.resetRequests[context] || (this.resetRequests[context] = crypto.randomUUID());
      await sendJsonData("/chat_reset", { context, request_id: requestId });
      delete this.resetRequests[context];

      // Increment reset counter
      if (typeof globalThis.resetCounter === 'number') {
        globalThis.resetCounter = globalThis.resetCounter + 1;
      }
    } catch (e) {
      toastFetchError("Error resetting chat", e);
    }
  },
};
Object.assign(chatsStore, changes);
