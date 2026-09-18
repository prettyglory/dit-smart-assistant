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

  // Voice input
  const [isListening, setIsListening] =
    useState(false);

  const [voiceLanguage, setVoiceLanguage] =
    useState("sw-TZ");

  // Speaker
  const [speakingIndex, setSpeakingIndex] =
    useState(null);

  const messagesEndRef =
    useRef(null);

  const recognitionRef =
    useRef(null);


  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);


  // Stop microphone and speaker when component closes
  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();

      if ("speechSynthesis" in window) {
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


    // Stop if already listening
    if (isListening) {
      recognitionRef.current?.stop();

      setIsListening(false);

      return;
    }


    const recognition =
      new SpeechRecognition();

    recognition.lang =
      voiceLanguage;

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

      setInput(transcript);
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
    };


    recognition.onend = () => {
      setIsListening(false);
    };


    recognitionRef.current =
      recognition;

    recognition.start();
  };


  // =====================================
  // SPEAKER / TEXT TO SPEECH
  // =====================================

  const cleanTextForSpeech = (
    text
  ) => {
    return text
      .replace(/#{1,6}\s?/g, "")
      .replace(/\*\*/g, "")
      .replace(/\*/g, "")
      .replace(/`/g, "")
      .replace(/\[(.*?)\]\(.*?\)/g, "$1")
      .replace(/[-•]\s/g, "")
      .replace(/\n+/g, ". ")
      .trim();
  };


  const detectSpeechLanguage = (
    text
  ) => {
    const lower =
      text.toLowerCase();

    const swahiliWords = [
      "na ",
      "kwa ",
      "ya ",
      "ni ",
      "katika ",
      "wanafunzi",
      "kujiunga",
      "ada",
      "masomo",
      "programu",
      "chuo",
      "kampasi",
      "sifa",
      "tafadhali",
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


    // Clicking same speaker stops it
    if (
      speakingIndex === index
    ) {
      window.speechSynthesis.cancel();

      setSpeakingIndex(null);

      return;
    }


    // Stop any previous speech
    window.speechSynthesis.cancel();


    const cleanText =
      cleanTextForSpeech(
        text
      );


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


    // Try to select matching browser voice
    const voices =
      window.speechSynthesis
        .getVoices();


    const preferredVoice =
      voices.find(
        (voice) =>
          voice.lang
            .toLowerCase()
            .startsWith(
              language
                .split("-")[0]
                .toLowerCase()
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


    // Stop speaking when a new question is sent
    if (
      "speechSynthesis"
      in window
    ) {
      window.speechSynthesis
        .cancel();

      setSpeakingIndex(
        null
      );
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
      setLoading(
        false
      );
    }
  };


  const sendMessage = () => {
    sendQuestion(
      input
    );
  };


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
      window.speechSynthesis
        .cancel();
    }

    setSpeakingIndex(
      null
    );
  };


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
            English, Kiswahili,
            or your voice.
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

                    <div className="assistant-actions">

                      <button
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
                      >

                        {speakingIndex ===
                        index
                          ? "⏹ Stop"
                          : "🔊 Listen"}

                      </button>

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
                  Searching verified DIT information...
                </div>

              </div>

            </div>

          )}


          <div
            ref={messagesEndRef}
          />

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

          <select
            className="voice-language"
            value={voiceLanguage}
            onChange={(event) =>
              setVoiceLanguage(
                event.target.value
              )
            }
            title="Voice language"
          >
            <option value="sw-TZ">
              SW
            </option>

            <option value="en-US">
              EN
            </option>
          </select>


          <button
            type="button"
            className={
              isListening
                ? "mic-button listening"
                : "mic-button"
            }
            onClick={
              startVoiceInput
            }
            disabled={loading}
            title={
              isListening
                ? "Stop listening"
                : "Speak your question"
            }
          >
            {isListening
              ? "⏹"
              : "🎤"}
          </button>


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
            placeholder={
              isListening
                ? "Listening..."
                : "Ask anything about DIT..."
            }
            rows="2"
          />


          <button
            className="send-button"
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