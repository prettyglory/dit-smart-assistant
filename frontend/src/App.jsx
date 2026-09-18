import {
  useEffect,
  useRef,
  useState,
} from "react";

import axios from "axios";
import "./App.css";


const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


const suggestedQuestions = [
  "DIT ina campuses ngapi?",
  "What programmes does DIT offer?",
  "How much is Bachelor tuition fee?",
  "Who gets priority for hostel accommodation?",
];


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

  const [loading, setLoading] =
    useState(false);

  const messagesEndRef = useRef(null);


  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);


  const sendQuestion = async (
    questionText
  ) => {
    const question =
      questionText.trim();

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
      const response =
        await axios.post(
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
          sources:
            response.data.sources || [],
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


  const sendMessage = () => {
    sendQuestion(input);
  };


  const handleKeyDown = (
    event
  ) => {
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

        <div className="brand">

          <img
            src="/dit-logo.png"
            alt="Dar es Salaam Institute of Technology logo"
            className="dit-logo"
          />

          <div className="brand-text">

            <h1>
              DIT Smart Assistant
            </h1>

            <p>
              Dar es Salaam Institute
              of Technology
            </p>

            <div className="certification">
              ISO 21001:2018 Certified
            </div>

          </div>

        </div>


        <div className="status">

          <span
            className="status-dot"
          />

          Online

        </div>

      </header>


      <main className="chat-container">

        <div className="welcome">

          <h2>
            How can I help you?
          </h2>

          <p>
            Get information from
            verified DIT sources.
          </p>

          <div className="suggestions">

            {suggestedQuestions.map(
              (question) => (
                <button
                  key={question}
                  className="suggestion-button"
                  onClick={() =>
                    sendQuestion(
                      question
                    )
                  }
                  disabled={loading}
                >
                  {question}
                </button>
              )
            )}

          </div>

        </div>


        <div className="messages">

          {messages.map(
            (message, index) => (

              <div
                key={index}
                className={
                  `message-row ${message.role}`
                }
              >

                <div className="message">

                  <div className="message-label">
                    {message.role ===
                    "user"
                      ? "You"
                      : "DIT Assistant"}
                  </div>


                  <div className="message-text">
                    {message.text}
                  </div>


                  {message.sources?.length >
                    0 && (

                    <div className="sources">

                      <strong>
                        Verified Sources
                      </strong>

                      {message.sources.map(
                        (
                          source,
                          sourceIndex
                        ) => (

                          <div
                            className="source"
                            key={
                              sourceIndex
                            }
                          >

                            <div>

                              {source.url ? (
                                <a
                                  href={
                                    source.url
                                  }
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  {
                                    source.title
                                  }
                                </a>
                              ) : (
                                <span>
                                  {
                                    source.title
                                  }
                                </span>
                              )}

                            </div>


                            <div className="source-meta">

                              {source.page && (
                                <span>
                                  Page{" "}
                                  {
                                    source.page
                                  }
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
            )
          )}


          {loading && (

            <div className="message-row assistant">

              <div className="message">

                <div className="message-label">
                  DIT Assistant
                </div>

                <div className="typing">
                  Searching verified
                  DIT information...
                </div>

              </div>

            </div>

          )}


          <div ref={messagesEndRef} />

        </div>


        <div className="input-area">

          <textarea
            value={input}
            onChange={(event) =>
              setInput(
                event.target.value
              )
            }
            onKeyDown={
              handleKeyDown
            }
            placeholder="Ask anything about DIT..."
            rows="2"
          />

          <button
            onClick={
              sendMessage
            }
            disabled={
              loading ||
              !input.trim()
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