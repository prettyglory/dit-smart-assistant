import { useState } from "react";
import axios from "axios";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text:
        "Hello! I am DIT Smart Assistant. " +
        "Ask me about DIT campuses, programmes, admissions, " +
        "fees, accommodation, regulations and academic information.",
      sources: [],
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    const question = input.trim();

    if (!question || loading) {
      return;
    }

    setMessages((current) => [
      ...current,
      {
        role: "user",
        text: question,
        sources: [],
      },
    ]);

    setInput("");
    setLoading(true);

    try {
      const response = await axios.post(
        `${API_URL}/api/chat`,
        {
          message: question,
        }
      );

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: response.data.answer,
          sources: response.data.sources || [],
        },
      ]);
    } catch (error) {
      console.error(error);

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text:
            "Sorry, I could not connect to the DIT Smart Assistant server.",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>DIT Smart Assistant</h1>
          <p>
            AI-powered information assistant for
            Dar es Salaam Institute of Technology
          </p>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          Online
        </div>
      </header>

      <main className="chat-container">
        <div className="messages">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`message-row ${message.role}`}
            >
              <div className="message">
                <div className="message-label">
                  {message.role === "user"
                    ? "You"
                    : "DIT Assistant"}
                </div>

                <div className="message-text">
                  {message.text}
                </div>

                {message.sources?.length > 0 && (
                  <div className="sources">
                    <strong>
                      Verified Sources
                    </strong>

                    {message.sources.map(
                      (source, sourceIndex) => (
                        <div
                          className="source"
                          key={sourceIndex}
                        >
                          <div>
                            {source.url ? (
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                {source.title}
                              </a>
                            ) : (
                              <span>
                                {source.title}
                              </span>
                            )}
                          </div>

                          <div className="source-meta">
                            {source.page && (
                              <span>
                                Page {source.page}
                              </span>
                            )}

                            {source.campus &&
                              source.campus !==
                                "unknown" && (
                                <span>
                                  {source.campus ===
                                  "all"
                                    ? "All campuses"
                                    : `${source.campus} Campus`}
                                </span>
                              )}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row assistant">
              <div className="message">
                <div className="message-label">
                  DIT Assistant
                </div>

                <div className="typing">
                  Searching verified DIT information...
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="input-area">
          <textarea
            value={input}
            onChange={(event) =>
              setInput(event.target.value)
            }
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about DIT..."
            rows="2"
          />

          <button
            onClick={sendMessage}
            disabled={
              loading || !input.trim()
            }
          >
            Send
          </button>
        </div>
      </main>
    </div>
  );
}

export default App;