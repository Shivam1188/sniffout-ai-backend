// static/js/mic_chat.js
document.addEventListener("DOMContentLoaded", function () {
  const messageHistory = document.getElementById("message-history");
  const recordButton = document.getElementById("record-button");
  const audioPlayer = document.getElementById("audio-player");
  const connectionStatus = document.getElementById("connection-status");

  let ws;
  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;
  let currentAssistantMessage = null;

  function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/audio_chat/${sessionId}/`;

    ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    ws.onopen = function () {
      console.log("WebSocket connected");
      updateStatus("Connected", "connected");
      createConversation();
    };

    ws.onclose = function (event) {
      console.warn("WebSocket disconnected:", event.code);
      updateStatus("Reconnecting...", "reconnecting");

      if (event.code !== 1000) {
        setTimeout(initWebSocket, 2000);
      }
    };

    ws.onmessage = function (event) {
      if (typeof event.data === "string") {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (error) {
          console.error("Invalid JSON:", error);
        }
      } else if (event.data instanceof ArrayBuffer) {
        playAudioResponse(event.data);
      }
    };

    ws.onerror = function (error) {
      console.error("WebSocket error:", error);
      updateStatus("Connection Error", "error");
    };
  }

  function createConversation() {
    fetch("/api/conversations/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        session_id: sessionId,
        title: "Voice Chat Session",
      }),
    }).catch((error) => console.warn("Error creating conversation:", error));
  }

  function getCsrfToken() {
    return (
      document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
      document.cookie.match(/csrftoken=([^;]*)/)?.[1] ||
      ""
    );
  }

  function updateStatus(text, className) {
    connectionStatus.textContent = text;
    connectionStatus.className = `status ${className}`;
  }

  function handleMessage(data) {
    console.log("Received:", data);

    switch (data.type) {
      case "transcription":
        addUserMessage(data.content, true); // voice message
        break;

      case "text_response":
        addAssistantMessage(data.content);
        break;

      case "text_chunk":
        if (!currentAssistantMessage) {
          currentAssistantMessage = createAssistantMessage("");
          messageHistory.appendChild(currentAssistantMessage);
        }
        currentAssistantMessage.textContent += data.content;
        scrollToBottom();
        break;

      case "text_complete":
        currentAssistantMessage = null;
        break;

      case "error":
        addErrorMessage(data.message);
        break;
    }
  }

  function playAudioResponse(arrayBuffer) {
    try {
      const blob = new Blob([arrayBuffer], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);

      audioPlayer.src = url;
      audioPlayer.play().catch((err) => {
        console.warn("Autoplay blocked:", err);
        addPlayButton(url);
      });

      audioPlayer.onended = () => URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Audio playback error:", error);
    }
  }

  function addPlayButton(audioUrl) {
    const playBtn = document.createElement("button");
    playBtn.textContent = "🔊 Click to Play Response";
    playBtn.className = "play-button";
    playBtn.onclick = () => {
      new Audio(audioUrl).play();
      playBtn.remove();
    };
    messageHistory.appendChild(playBtn);
    scrollToBottom();
  }

  function addUserMessage(content, isVoice = false) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "user-message";

    if (isVoice) {
      messageDiv.innerHTML = `<span class="voice-indicator">🎤</span> ${content}`;
    } else {
      messageDiv.textContent = content;
    }

    messageHistory.appendChild(messageDiv);
    scrollToBottom();
  }

  function addAssistantMessage(content) {
    const messageDiv = createAssistantMessage(content);
    messageHistory.appendChild(messageDiv);
    scrollToBottom();
    currentAssistantMessage = null;
  }

  function createAssistantMessage(content) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "assistant-message";
    messageDiv.textContent = content;
    return messageDiv;
  }

  function addErrorMessage(content) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "error-message";
    messageDiv.textContent = `❌ ${content}`;
    messageHistory.appendChild(messageDiv);
    scrollToBottom();
  }

  function addSystemMessage(content) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "system-message";
    messageDiv.textContent = content;
    messageHistory.appendChild(messageDiv);
    scrollToBottom();
    return messageDiv;
  }

  function scrollToBottom() {
    messageHistory.scrollTop = messageHistory.scrollHeight;
  }

  // Main recording functionality
  recordButton.addEventListener("click", async function () {
    if (!isRecording) {
      await startRecording();
    } else {
      stopRecording();
    }
  });

  async function startRecording() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addErrorMessage("Not connected to server");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // Use webm format for better browser support
      const options = { mimeType: "audio/webm;codecs=opus" };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options.mimeType = "audio/webm";
      }

      mediaRecorder = new MediaRecorder(stream, options);
      audioChunks = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, {
          type: mediaRecorder.mimeType,
        });
        sendAudioToServer(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.onerror = (event) => {
        console.error("Recording error:", event.error);
        addErrorMessage("Recording failed");
        resetRecording();
      };

      mediaRecorder.start();
      isRecording = true;

      recordButton.textContent = "🛑 Stop & Send";
      recordButton.className = "record-button recording";
      updateStatus("Recording...", "recording");

      addSystemMessage("🎤 Listening...");
    } catch (error) {
      console.error("Microphone error:", error);
      addErrorMessage(`Microphone access denied: ${error.message}`);
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
    recordButton.textContent = "🎤 Click to Speak";
    recordButton.className = "record-button";
    updateStatus(
      ws?.readyState === WebSocket.OPEN ? "Connected" : "Disconnected",
      ws?.readyState === WebSocket.OPEN ? "connected" : "disconnected"
    );
  }

  function sendAudioToServer(audioBlob) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addErrorMessage("Connection lost");
      return;
    }

    console.log(
      `Sending audio: ${audioBlob.size} bytes, type: ${audioBlob.type}`
    );

    const processingMsg = addSystemMessage("🔄 Processing your voice...");

    // Send start message
    ws.send(
      JSON.stringify({
        type: "start_audio",
        size: audioBlob.size,
        mime_type: audioBlob.type,
      })
    );

    // Send audio data
    const reader = new FileReader();
    reader.onload = () => {
      try {
        ws.send(reader.result);
        ws.send(JSON.stringify({ type: "end_audio" }));
      } catch (error) {
        console.error("Send error:", error);
        addErrorMessage("Failed to send audio");
      }
    };

    reader.onerror = () => {
      addErrorMessage("Failed to read audio");
    };

    reader.readAsArrayBuffer(audioBlob);

    // Remove processing message after timeout
    setTimeout(() => {
      if (processingMsg.parentNode) {
        processingMsg.remove();
      }
    }, 10000);
  }

  // Initialize
  initWebSocket();

  // Cleanup
  window.addEventListener("beforeunload", () => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.close(1000);
    }
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
    }
  });
});
