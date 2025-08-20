// static/js/audio_chat.js
document.addEventListener("DOMContentLoaded", function () {
  const messageHistory = document.getElementById("message-history");
  const textForm = document.getElementById("text-form");
  const textInput = document.getElementById("text-input");
  const recordButton = document.getElementById("record-button");
  const audioPlayer = document.getElementById("audio-player");
  const connectionStatus = document.getElementById("connection-status");

  let ws;
  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;
  let audioContext;
  let currentAssistantMessageElement = null;

  function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/audio_chat/${sessionId}/`;

    ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    ws.onopen = function () {
      console.log("WebSocket connected");
      connectionStatus.textContent = "Connected";
      connectionStatus.className = "status connected";
      loadMessageHistory();
    };

    ws.onclose = function (event) {
      console.warn("WebSocket disconnected, code:", event.code);
      connectionStatus.textContent = "Disconnected — reconnecting...";
      connectionStatus.className = "status disconnected";

      // Only reconnect if it wasn't a manual close
      if (event.code !== 1000) {
        setTimeout(initWebSocket, 3000);
      }
    };

    ws.onmessage = function (event) {
      if (typeof event.data === "string") {
        try {
          const data = JSON.parse(event.data);
          handleServerMessage(data);
        } catch (error) {
          console.error("Invalid JSON message:", event.data, error);
        }
      } else if (event.data instanceof ArrayBuffer) {
        handleAudioResponse(event.data);
      }
    };

    ws.onerror = function (error) {
      console.error("WebSocket error:", error);
      connectionStatus.textContent = "Connection Error";
      connectionStatus.className = "status error";
    };
  }

  function loadMessageHistory() {
    // Try the correct API endpoint first
    fetch(`/api/conversations/${sessionId}/messages/`)
      .then((response) => {
        if (response.ok) {
          return response.json();
        } else if (response.status === 404) {
          // If conversation doesn't exist, create it
          return createConversation().then(() => []);
        }
        throw new Error(`HTTP ${response.status}`);
      })
      .then((messages) => {
        messageHistory.innerHTML = "";
        messages.forEach((msg) => appendMessage(msg));
        scrollToBottom();
      })
      .catch((error) => {
        console.error("Error loading messages:", error);
        // Don't fail silently, but don't block the interface
        messageHistory.innerHTML =
          '<div class="system-message">Starting new conversation...</div>';
      });
  }

  function createConversation() {
    return fetch("/api/conversations/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        session_id: sessionId,
        title: "Audio Chat Session",
      }),
    }).then((response) => {
      if (!response.ok) {
        throw new Error("Failed to create conversation");
      }
      return response.json();
    });
  }

  function getCsrfToken() {
    return (
      document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
      document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1] ||
      ""
    );
  }

  function handleServerMessage(data) {
    console.log("Received message:", data);

    switch (data.type) {
      case "text_response":
        appendMessage({ text_response: data.content, is_assistant: true });
        break;

      case "text_chunk":
        // Handle streaming text response
        if (!currentAssistantMessageElement) {
          currentAssistantMessageElement = createAssistantMessage("");
          messageHistory.appendChild(currentAssistantMessageElement);
        }
        appendToCurrentMessage(data.content);
        break;

      case "text_complete":
        // Finalize streaming response
        currentAssistantMessageElement = null;
        scrollToBottom();
        break;

      case "audio_response":
        // Audio response received
        handleAudioResponse(data.audio_data);
        break;

      case "error":
        displayError(data.message || "An error occurred");
        break;

      case "transcription":
        // Show what was understood from voice input
        appendMessage({
          text_input: data.content,
          is_user: true,
          source: "voice",
        });
        break;

      default:
        console.warn("Unknown message type:", data.type);
    }
  }

  function handleAudioResponse(arrayBuffer) {
    try {
      const blob = new Blob([arrayBuffer], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      audioPlayer.src = url;

      audioPlayer.play().catch((err) => {
        console.warn("Autoplay blocked:", err);
        // Show a play button or notification to user
        showPlayButton(url);
      });

      // Clean up URL after playing
      audioPlayer.onended = () => URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error handling audio response:", error);
    }
  }

  function showPlayButton(audioUrl) {
    const playButton = document.createElement("button");
    playButton.textContent = "🔊 Play Response";
    playButton.className = "play-audio-btn";
    playButton.onclick = () => {
      const audio = new Audio(audioUrl);
      audio.play();
      playButton.remove();
    };
    messageHistory.appendChild(playButton);
    scrollToBottom();
  }

  function appendMessage(msg) {
    if (msg.text_input || (msg.is_user && msg.content)) {
      const userMsg = createUserMessage(
        msg.text_input || msg.content,
        msg.source
      );
      messageHistory.appendChild(userMsg);
    }

    if (msg.text_response || (msg.is_assistant && msg.content)) {
      const assistantMsg = createAssistantMessage(
        msg.text_response || msg.content
      );
      messageHistory.appendChild(assistantMsg);
    }

    scrollToBottom();
  }

  function createUserMessage(content, source = "text") {
    const userMsg = document.createElement("div");
    userMsg.className = "user-message";

    if (source === "voice") {
      userMsg.innerHTML = `<span class="voice-indicator">🎤</span> ${content}`;
    } else {
      userMsg.textContent = content;
    }

    return userMsg;
  }

  function createAssistantMessage(content) {
    const assistantMsg = document.createElement("div");
    assistantMsg.className = "assistant-message";
    assistantMsg.textContent = content;
    return assistantMsg;
  }

  function appendToCurrentMessage(content) {
    if (currentAssistantMessageElement) {
      currentAssistantMessageElement.textContent += content;
      scrollToBottom();
    }
  }

  function scrollToBottom() {
    messageHistory.scrollTop = messageHistory.scrollHeight;
  }

  function displayError(message) {
    const errorMsg = document.createElement("div");
    errorMsg.className = "error-message";
    errorMsg.textContent = `Error: ${message}`;
    messageHistory.appendChild(errorMsg);
    scrollToBottom();
  }

  // Text form submission
  textForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const text = textInput.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

    // Display user message immediately
    appendMessage({ text_input: text, is_user: true });

    // Send to server
    ws.send(
      JSON.stringify({
        type: "text_message",
        content: text,
      })
    );

    textInput.value = "";
  });

  // Audio recording
  recordButton.addEventListener("click", async function () {
    if (!isRecording) {
      await startRecording();
    } else {
      stopRecording();
    }
  });

  async function startRecording() {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      // Initialize audio context for better control
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }

      // Create MediaRecorder with specific options
      const options = {
        mimeType: "audio/webm;codecs=opus", // Better compression
        audioBitsPerSecond: 16000,
      };

      // Fallback for Safari
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options.mimeType = "audio/mp4";
      }

      mediaRecorder = new MediaRecorder(stream, options);
      audioChunks = [];

      mediaRecorder.ondataavailable = function (event) {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = function () {
        const audioBlob = new Blob(audioChunks, {
          type: mediaRecorder.mimeType || "audio/webm",
        });
        sendAudioToServer(audioBlob);

        // Clean up stream
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.onerror = function (event) {
        console.error("MediaRecorder error:", event.error);
        displayError("Recording failed: " + event.error.message);
        resetRecording();
      };

      mediaRecorder.start(1000); // Collect data every second
      isRecording = true;
      recordButton.textContent = "🛑 Stop Recording";
      recordButton.className = "record-button recording";

      // Show recording indicator
      connectionStatus.textContent = "Recording...";
      connectionStatus.className = "status recording";
    } catch (error) {
      console.error("Error starting recording:", error);
      displayError("Could not access microphone: " + error.message);
      resetRecording();
    }
  }

  function stopRecording() {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      resetRecording();
    }
  }

  function resetRecording() {
    isRecording = false;
    recordButton.textContent = "🎤 Start Recording";
    recordButton.className = "record-button";
    connectionStatus.textContent =
      ws?.readyState === WebSocket.OPEN ? "Connected" : "Disconnected";
    connectionStatus.className = `status ${
      ws?.readyState === WebSocket.OPEN ? "connected" : "disconnected"
    }`;
  }

  function sendAudioToServer(audioBlob) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      displayError("WebSocket not connected");
      return;
    }

    console.log(
      "Sending audio blob:",
      audioBlob.size,
      "bytes, type:",
      audioBlob.type
    );

    // Send start message with metadata
    ws.send(
      JSON.stringify({
        type: "audio_start",
        size: audioBlob.size,
        mime_type: audioBlob.type,
        format: "webm",
      })
    );

    // Convert and send audio data
    const reader = new FileReader();
    reader.onload = function () {
      try {
        ws.send(reader.result); // Send as ArrayBuffer
        ws.send(JSON.stringify({ type: "audio_end" }));

        // Show processing indicator
        const processingMsg = document.createElement("div");
        processingMsg.className = "system-message processing";
        processingMsg.textContent = "Processing audio...";
        messageHistory.appendChild(processingMsg);
        scrollToBottom();

        // Remove processing message after timeout
        setTimeout(() => {
          if (processingMsg.parentNode) {
            processingMsg.remove();
          }
        }, 10000);
      } catch (error) {
        console.error("Error sending audio:", error);
        displayError("Failed to send audio");
      }
    };

    reader.onerror = function () {
      displayError("Failed to read audio file");
    };

    reader.readAsArrayBuffer(audioBlob);
  }

  // Initialize connection
  initWebSocket();

  // Cleanup on page unload
  window.addEventListener("beforeunload", function () {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close(1000);
    }
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
    }
  });
});
