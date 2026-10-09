import axios from "axios";


const SESSION_STORAGE_KEY =
  "dit_agent_session_id";


const isChatRequest = (config) => {
  const method =
    config.method?.toLowerCase();

  const url =
    config.url || "";

  return (
    method === "post" &&
    /\/api\/chat\/?$/.test(url)
  );
};


const getHistory = (config) => {
  const history =
    config.data?.history;

  return Array.isArray(history)
    ? history
    : [];
};


axios.interceptors.request.use(
  (config) => {
    if (!isChatRequest(config)) {
      return config;
    }

    const history =
      getHistory(config);

    const hasUserHistory =
      history.some(
        (message) =>
          message?.role === "user"
      );

    const previousSessionId =
      sessionStorage.getItem(
        SESSION_STORAGE_KEY
      );

    // App.jsx resets the visible transcript to only the welcome
    // assistant message when Clear Chat is pressed. Treat the next
    // outgoing request as a new session and expire the old server state.
    if (
      !hasUserHistory &&
      previousSessionId
    ) {
      const baseUrl =
        (config.url || "").replace(
          /\/api\/chat\/?$/,
          ""
        );

      fetch(
        `${baseUrl}/api/sessions/${encodeURIComponent(previousSessionId)}`,
        {
          method: "DELETE",
        }
      ).catch(
        (error) => {
          console.warn(
            "Could not clear previous chat session:",
            error
          );
        }
      );

      sessionStorage.removeItem(
        SESSION_STORAGE_KEY
      );
    }

    const sessionId =
      sessionStorage.getItem(
        SESSION_STORAGE_KEY
      );

    if (sessionId) {
      config.data = {
        ...config.data,
        session_id: sessionId,
      };
    }

    return config;
  }
);


axios.interceptors.response.use(
  (response) => {
    if (
      isChatRequest(response.config) &&
      response.data?.session_id
    ) {
      sessionStorage.setItem(
        SESSION_STORAGE_KEY,
        response.data.session_id
      );
    }

    return response;
  }
);
