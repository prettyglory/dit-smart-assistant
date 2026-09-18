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
  "What are the requirements for joining DIT?",
  "How much is Bachelor tuition fee?",
];


function App() {
  const [messages, setMessages] =
    useState([initialMessage]);

  const [input, setInput] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [isListening, setIsListening] =
    useState(false);

  const [speakingIndex, setSpeakingIndex] =
    useState(null);


  const messagesEndRef =
    useRef(null);

  const recognitionRef =
    useRef(null);

  const textareaRef =
    useRef(null);


  // =====================================
  // AUTO SCROLL
  // =====================================

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);


  // =====================================
  // AUTO RESIZE TEXTAREA
  // =====================================

  useEffect(() => {
    const textarea =
      textareaRef.current;

    if (!textarea) {
      return;
    }

    textarea.style.height =
      "auto";

    textarea.style.height =
      `${Math.min(
        textarea.scrollHeight,
        150
      )}px`;
  }, [input]);


  // =====================================
  // CLEAN UP VOICE SERVICES
  // =====================================

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();

      if (
        "speechSynthesis" in window
      ) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);


  // =====================================
  // VOICE INPUT
  // =====================================

  const startVoiceInput = () => {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;


    if (!SpeechRecognition) {
      alert(
        "Voice recognition is not supported by this browser. " +
        "Please use Google Chrome or Microsoft Edge."
      );

      return;
    }


    if (isListening) {
      recognitionRef.current?.stop();

      return;
    }


    const recognition =
      new SpeechRecognition();


    recognition.lang =
      navigator.language ||
      "en-US";

    recognition.continuous =
      false;

    recognition.interimResults =
      false;

    recognition.maxAlternatives =
      1;


    recognition.onstart = () => {
      setIsListening(true);
    };


    recognition.onresult = (
      event
    ) => {
      const transcript =
        event.results[0][0]
          .transcript;


      setInput(
        (currentInput) => {
          if (
            currentInput.trim()
          ) {
            return (
              `${currentInput.trim()} ${transcript}`
            );
          }

          return transcript;
        }
      );
    };


    recognition.onerror = (
      event
    ) => {
      console.error(
        "Speech recognition error:",
        event.error
      );

      setIsListening(false);


      if (
        event.error ===
        "not-allowed"
      ) {
        alert(
          "Microphone permission was denied. " +
          "Please allow microphone access in your browser."
        );
      }


      if (
        event.error ===
        "no-speech"
      ) {
        console.log(
          "No speech was detected."
        );
      }
    };


    recognition.onend = () => {
      setIsListening(false);
    };


    recognitionRef.current =
      recognition;


    try {
      recognition.start();
    } catch (error) {
      console.error(
        "Could not start microphone:",
        error
      );

      setIsListening(false);
    }
  };


  // =====================================
  // CLEAN TEXT FOR SPEAKER
  // =====================================

  const cleanTextForSpeech = (
    text
  ) => {
    return text
      .replace(/#{1,6}\s?/g, "")
      .replace(/\*\*/g, "")
      .replace(/\*/g, "")
      .replace(/`/g, "")
      .replace(
        /\[(.*?)\]\(.*?\)/g,
        "$1"
      )
      .replace(/[-•]\s/g, "")
      .replace(/\n+/g, ". ")
      .trim();
  };


  // =====================================
  // LANGUAGE DETECTION FOR SPEAKER
  // =====================================

  const detectSpeechLanguage = (
    text
  ) => {
    const lower =
      ` ${text.toLowerCase()} `;


    const swahiliWords = [
      " kwa ",
      " ya ",
      " ni ",
      " na ",
      " katika ",
      " mwanafunzi ",
      " wanafunzi ",
      " kujiunga ",
      " ada ",
      " masomo ",
      " chuo ",
      " kampasi ",
      " sifa ",
      " unaweza ",
      " programu ",
      " taarifa ",
      " kuhusu ",
      " tafadhali ",
    ];


    const hasSwahili =
      swahiliWords.some(
        (word) =>
          lower.includes(word)
      );


    return hasSwahili
      ? "sw-TZ"
      : "en-US";
  };


  // =====================================
  // TEXT TO SPEECH
  // =====================================

  const speakMessage = (
    text,
    index
  ) => {
    if (
      !(
        "speechSynthesis"
        in window
      )
    ) {
      alert(
        "Text-to-speech is not supported by this browser."
      );

      return;
    }


    if (
      speakingIndex === index
    ) {
      window.speechSynthesis.cancel();

      setSpeakingIndex(null);

      return;
    }


    window.speechSynthesis.cancel();


    const cleanText =
      cleanTextForSpeech(
        text
      );


    if (!cleanText) {
      return;
    }


    const utterance =
      new SpeechSynthesisUtterance(
        cleanText
      );


    const language =
      detectSpeechLanguage(
        cleanText
      );


    utterance.lang =
      language;

    utterance.rate =
      0.95;

    utterance.pitch =
      1;

    utterance.volume =
      1;


    const voices =
      window.speechSynthesis
        .getVoices();


    const languagePrefix =
      language
        .split("-")[0]
        .toLowerCase();


    const preferredVoice =
      voices.find(
        (voice) =>
          voice.lang
            .toLowerCase()
            .startsWith(
              languagePrefix
            )
      );


    if (preferredVoice) {
      utterance.voice =
        preferredVoice;
    }


    utterance.onstart =
      () => {
        setSpeakingIndex(
          index
        );
      };


    utterance.onend =
      () => {
        setSpeakingIndex(
          null
        );
      };


    utterance.onerror =
      () => {
        setSpeakingIndex(
          null
        );
      };


    window.speechSynthesis
      .speak(
        utterance
      );
  };


  // =====================================
  // SEND QUESTION
  // =====================================

  const sendQuestion = async (
    questionText
  ) => {
    const question =
      questionText.trim();


    if (
      !question ||
      loading
    ) {
      return;
    }


    if (isListening) {
      recognitionRef.current?.stop();
    }


    if (
      "speechSynthesis"
      in window
    ) {
      window.speechSynthesis.cancel();

      setSpeakingIndex(null);
    }


    const history =
      messages
        .slice(-6)
        .map(
          (message) => ({
            role:
              message.role,

            content:
              message.text,
          })
        );


    const userMessage = {
      role: "user",

      text: question,

      sources: [],

      feedback: null,
    };


    setMessages(
      (current) => [
        ...current,
        userMessage,
      ]
    );


    setInput("");

    setLoading(true);


    try {
      const response =
        await axios.post(
          `${API_URL}/api/chat`,
          {
            message:
              question,

            history:
              history,
          }
        );


      const assistantMessage = {
        role: "assistant",

        text:
          response.data.answer,

        sources:
          response.data.sources ||
          [],

        feedback: null,
      };


      setMessages(
        (current) => [
          ...current,
          assistantMessage,
        ]
      );
    } catch (error) {
      console.error(
        "Chat request failed:",
        error
      );


      setMessages(
        (current) => [
          ...current,

          {
            role:
              "assistant",

            text:
              "Sorry, I could not connect to the DIT Smart Assistant server.\n\n" +
              "Please make sure the backend server is running.",

            sources: [],

            feedback:
              null,
          },
        ]
      );
    } finally {
      setLoading(false);
    }
  };


  const sendMessage = () => {
    sendQuestion(
      input
    );
  };


  // =====================================
  // CLEAR CHAT
  // =====================================

  const clearChat = () => {
    setMessages([
      initialMessage,
    ]);

    setInput("");


    recognitionRef.current?.stop();

    setIsListening(false);


    if (
      "speechSynthesis"
      in window
    ) {
      window.speechSynthesis.cancel();
    }


    setSpeakingIndex(null);
  };


  // =====================================
  // FEEDBACK
  // =====================================

  const handleFeedback = (
    messageIndex,
    feedbackValue
  ) => {
    setMessages(
      (current) =>
        current.map(
          (
            message,
            index
          ) => {
            if (
              index !==
              messageIndex
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


  // =====================================
  // ENTER TO SEND
  // =====================================

  const handleKeyDown = (
    event
  ) => {
    if (
      event.key ===
        "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      sendMessage();
    }
  };


  return (
    <div className="app">

      {/* =====================================
          HEADER
          ===================================== */}

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


      {/* =====================================
          MAIN CHAT
          ===================================== */}

      <main className="chat-container">

        {/* =====================================
            WELCOME
            ===================================== */}

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


        {/* =====================================
            MESSAGES
            ===================================== */}

        <div className="messages">

          {messages.map(
            (
              message,
              index
            ) => (

              <div
                key={index}
                className={
                  `message-row ${message.role}`
                }
              >

                <div className="message">

                  {/* Message label */}

                  <div className="message-label">

                    {message.role ===
                    "user"
                      ? "You"
                      : "DIT Assistant"}

                  </div>


                  {/* Message content */}

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


                  {/* =====================================
                      VERIFIED SOURCES
                      ===================================== */}

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


                  {/* =====================================
                      SPEAKER
                      ===================================== */}

                  {message.role ===
                    "assistant" &&
                    index !== 0 && (

                    <div className="assistant-actions">

                      <button
                        type="button"
                        className={
                          speakingIndex ===
                          index
                            ? "speaker-button speaking"
                            : "speaker-button"
                        }
                        onClick={() =>
                          speakMessage(
                            message.text,
                            index
                          )
                        }
                        title={
                          speakingIndex ===
                          index
                            ? "Stop reading"
                            : "Read answer aloud"
                        }
                        aria-label={
                          speakingIndex ===
                          index
                            ? "Stop reading"
                            : "Read answer aloud"
                        }
                      >

                        {speakingIndex ===
                        index ? (

                          <>
                            <span>
                              ■
                            </span>

                            <span>
                              Stop
                            </span>
                          </>

                        ) : (

                          <>
                            {/* Speaker icon */}

                            <svg
                              viewBox="0 0 24 24"
                              width="18"
                              height="18"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              aria-hidden="true"
                            >

                              <polygon
                                points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"
                              />

                              <path
                                d="M15.54 8.46a5 5 0 0 1 0 7.07"
                              />

                              <path
                                d="M19.07 4.93a10 10 0 0 1 0 14.14"
                              />

                            </svg>


                            <span>
                              Listen
                            </span>
                          </>

                        )}

                      </button>

                    </div>

                  )}


                  {/* =====================================
                      FEEDBACK
                      ===================================== */}

                  {message.role ===
                    "assistant" &&
                    index !== 0 && (

                    <div className="feedback-area">

                      <span className="feedback-label">
                        Was this helpful?
                      </span>


                      <button
                        type="button"
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
                        type="button"
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


          {/* =====================================
              LOADING
              ===================================== */}

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


          <div
            ref={messagesEndRef}
          />

        </div>


        {/* =====================================
            DISCLAIMER
            ===================================== */}

        <div className="disclaimer">

          DIT Smart Assistant provides
          information from available
          verified DIT sources.
          For official decisions,
          confirm critical information
          through the relevant DIT office
          or official DIT website.

        </div>


        {/* =====================================
            CHAT COMPOSER
            ===================================== */}

        <div className="input-area">

          <div className="composer">

            {/* Text input */}

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(event) =>
                setInput(
                  event.target.value
                )
              }
              onKeyDown={
                handleKeyDown
              }
              placeholder={
                isListening
                  ? "Listening..."
                  : "Ask anything about DIT..."
              }
              rows="1"
            />


            {/* Right side actions */}

            <div className="composer-actions">

              {/* =====================================
                  MICROPHONE
                  ===================================== */}

              <button
                type="button"
                className={
                  isListening
                    ? "voice-button listening"
                    : "voice-button"
                }
                onClick={
                  startVoiceInput
                }
                disabled={loading}
                title={
                  isListening
                    ? "Stop listening"
                    : "Use voice"
                }
                aria-label={
                  isListening
                    ? "Stop listening"
                    : "Use microphone"
                }
              >

                {isListening ? (

                  <span
                    className="voice-stop"
                  />

                ) : (

                  <svg
                    viewBox="0 0 24 24"
                    width="22"
                    height="22"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >

                    <rect
                      x="9"
                      y="2"
                      width="6"
                      height="12"
                      rx="3"
                    />

                    <path
                      d="M5 10a7 7 0 0 0 14 0"
                    />

                    <path
                      d="M12 17v4"
                    />

                    <path
                      d="M9 21h6"
                    />

                  </svg>

                )}

              </button>


              {/* =====================================
                  SEND
                  ===================================== */}

              <button
                type="button"
                className="send-button"
                onClick={
                  sendMessage
                }
                disabled={
                  loading ||
                  !input.trim()
                }
                aria-label="Send message"
                title="Send"
              >

                <svg
                  viewBox="0 0 24 24"
                  width="20"
                  height="20"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >

                  <path
                    d="M12 19V5"
                  />

                  <path
                    d="M6 11l6-6 6 6"
                  />

                </svg>

              </button>

            </div>

          </div>

        </div>

      </main>

    </div>
  );
}


export default App;