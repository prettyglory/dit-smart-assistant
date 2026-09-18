import {
  useEffect,
  useRef,
  useState,
} from "react";

import axios from "axios";
import ReactMarkdown from "react-markdown";
import "./App.css";


const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


const initialMessage = {
  role: "assistant",
  text:
    "Hello! Karibu DIT Smart Assistant 👋\n\n" +
    "You can ask me about **DIT campuses, programmes, " +
    "admissions, fees, accommodation, regulations, " +
    "IPT and academic information**.\n\n" +
    "Unaweza kuuliza kwa **English au Kiswahili**.",
  sources: [],
  feedback: null,
};


const suggestedQuestions = [
  "DIT ina campuses ngapi?",
  "What programmes does DIT offer?",
  "How much is Bachelor tuition fee?",
  "Who gets priority for hostel accommodation?",
];


function App() {
  const [messages, setMessages] =
    useState([initialMessage]);

  const [input, setInput] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const messagesEndRef =
    useRef(null);


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


    const history = messages
      .slice(-6)
      .map((message) => ({
        role: message.role,
        content: message.text,
      }));


    const userMessage = {
      role: "user",
      text: question,
      sources: [],
      feedback: null,
    };


    setMessages((current) => [
      ...current,
      userMessage,
    ]);

    setInput("");
    setLoading(true);


    try {
      const response =
        await axios.post(
          `${API_URL}/api/chat`,
          {
            message: question,
            history: history,
          }
        );


      const assistantMessage = {
        role: "assistant",
        text: response.data.answer,
        sources:
          response.data.sources || [],
        feedback: null,
      };


      setMessages((current) => [
        ...current,
        assistantMessage,
      ]);
    } catch (error) {
      console.error(
        "Chat request failed:",
        error
      );


      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text:
            "Sorry, I could not connect to the DIT Smart Assistant server.\n\n" +
            "Please make sure the backend server is running.",
          sources: [],
          feedback: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };


  const sendMessage = () => {
    sendQuestion(input);
  };


  const clearChat = () => {
    setMessages([
      initialMessage,
    ]);

    setInput("");
  };


  const handleFeedback = (
    messageIndex,
    feedbackValue
  ) => {
    setMessages((current) =>
      current.map(
        (message, index) => {
          if (
            index !== messageIndex
          ) {
            return message;
          }

          return {
            ...message,

            feedback:
              message.feedback ===
              feedbackValue
                ? null
                : feedbackValue,
          };
        }
      )
    );
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


        <div className="header-actions">

          <div className="status">

            <span
              className="status-dot"
            />

            Online

          </div>


          <button
            className="clear-button"
            onClick={clearChat}
            disabled={loading}
          >
            Clear Chat
          </button>

        </div>

      </header>


      <main className="chat-container">

        <div className="welcome">

          <h2>
            How can I help you?
          </h2>

          <p>
            Ask questions using
            English or Kiswahili.
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

                    {message.role ===
                    "assistant" ? (

                      <ReactMarkdown>
                        {message.text}
                      </ReactMarkdown>

                    ) : (

                      message.text

                    )}

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
                              `${source.title}-${source.page}-${sourceIndex}`
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


                  {message.role ===
                    "assistant" &&
                    index !== 0 && (

                    <div className="feedback-area">

                      <span className="feedback-label">
                        Was this helpful?
                      </span>


                      <button
                        className={
                          message.feedback ===
                          "positive"
                            ? "feedback-button active"
                            : "feedback-button"
                        }
                        onClick={() =>
                          handleFeedback(
                            index,
                            "positive"
                          )
                        }
                        aria-label="Helpful answer"
                        title="Helpful"
                      >
                        👍
                      </button>


                      <button
                        className={
                          message.feedback ===
                          "negative"
                            ? "feedback-button active"
                            : "feedback-button"
                        }
                        onClick={() =>
                          handleFeedback(
                            index,
                            "negative"
                          )
                        }
                        aria-label="Not helpful answer"
                        title="Not helpful"
                      >
                        👎
                      </button>


                      {message.feedback && (
                        <span className="feedback-thanks">
                          Thanks for your feedback.
                        </span>
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


        <div className="disclaimer">

          DIT Smart Assistant provides
          information from available
          verified DIT sources.
          For official decisions,
          confirm critical information
          through the relevant DIT office
          or official DIT website.

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