// static/js/mic_chat.js
document.addEventListener("DOMContentLoaded", function () {
  const messageHistory = document.getElementById("message-history");
  const recordButton = document.getElementById("record-button");
  const connectionStatus = document.getElementById("connection-status");
  const volumeIndicator = document.getElementById("volume-indicator"); // Add this element

  let ws;
  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;
  let audioContext;
  let currentAudio = null;

  function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/audio_chat/${sessionId}/`;

    ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    ws.onopen = function () {
      console.log("WebSocket connected");
      updateStatus("Connected - Ready for voice chat!", "connected");
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

  function updateStatus(text, className) {
    connectionStatus.textContent = text;
    connectionStatus.className = `status ${className}`;
  }

  function handleMessage(data) {
    console.log("Received:", data);

    switch (data.type) {
      case "transcription":
        addUserMessage(data.content, true);
        break;

      case "voice_response":
        // Show the text version of the response
        addAssistantMessage(data.text, true); // true indicates it's a voice message
        if (!data.has_audio) {
          // If no audio is coming, use text-to-speech fallback
          speakText(data.text);
        }
        break;

      case "text_response":
        addAssistantMessage(data.content, data.tts_failed);
        if (data.tts_failed) {
          // Fallback to browser TTS
          speakText(data.content);
        }
        break;

      case "error":
        addErrorMessage(data.message);
        break;
    }
  }

  function playAudioResponse(arrayBuffer) {
    try {
      // Stop any currently playing audio
      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
      }

      const blob = new Blob([arrayBuffer], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);

      currentAudio = new Audio(url);

      // Add visual feedback
      updateStatus("🔊 Assistant speaking...", "speaking");

      currentAudio
        .play()
        .then(() => {
          console.log("Playing voice response");
        })
        .catch((err) => {
          console.warn("Autoplay blocked:", err);
          addPlayButton(url);
        });

      currentAudio.onended = () => {
        URL.revokeObjectURL(url);
        updateStatus("Ready for your voice", "connected");
        currentAudio = null;
      };

      currentAudio.onerror = (error) => {
        console.error("Audio playback error:", error);
        updateStatus("Audio playback failed", "error");
        URL.revokeObjectURL(url);
      };
    } catch (error) {
      console.error("Audio processing error:", error);
      updateStatus("Audio processing failed", "error");
    }
  }

  function speakText(text) {
    // Browser fallback TTS
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel(); // Stop any current speech

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      utterance.onstart = () => {
        updateStatus("🔊 Assistant speaking...", "speaking");
      };

      utterance.onend = () => {
        updateStatus("Ready for your voice", "connected");
      };

      window.speechSynthesis.speak(utterance);
    }
  }

  function addPlayButton(audioUrl) {
    const playBtn = document.createElement("button");
    playBtn.textContent = "🔊 Click to Play Voice Response";
    playBtn.className = "play-button";
    playBtn.onclick = () => {
      const audio = new Audio(audioUrl);
      audio.play();
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

  function addAssistantMessage(content, isVoice = false) {
    const messageDiv = document.createElement("div");
    messageDiv.className = "assistant-message";

    if (isVoice) {
      messageDiv.innerHTML = `<span class="voice-indicator">🔊</span> ${content}`;
    } else {
      messageDiv.textContent = content;
    }

    messageHistory.appendChild(messageDiv);
    scrollToBottom();
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

  // Enhanced recording with visual feedback
  recordButton.addEventListener("click", async function () {
    if (!isRecording) {
      await startRecording();
    } else {
      stopRecording();
    }
  });

  // Add keyboard shortcut (Space bar to record)
  document.addEventListener("keydown", function (e) {
    if (e.code === "Space" && !e.target.matches("input, textarea")) {
      e.preventDefault();
      if (!isRecording) {
        startRecording();
      }
    }
  });

  document.addEventListener("keyup", function (e) {
    if (e.code === "Space" && !e.target.matches("input, textarea")) {
      e.preventDefault();
      if (isRecording) {
        stopRecording();
      }
    }
  });

  async function startRecording() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addErrorMessage("Not connected to server");
      return;
    }

    // Stop any playing audio when user starts speaking
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
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

      recordButton.textContent = "🛑 Release to Send";
      recordButton.className = "record-button recording pulse";
      updateStatus("🎤 Listening... (Release to send)", "recording");

      // Visual feedback
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
      updateStatus("🔄 Processing your voice...", "processing");
    }
  }

  function resetRecording() {
    isRecording = false;
    recordButton.textContent = "🎤 Hold to Speak";
    recordButton.className = "record-button";
  }

  function sendAudioToServer(audioBlob) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addErrorMessage("Connection lost");
      return;
    }

    console.log(
      `Sending audio: ${audioBlob.size} bytes, type: ${audioBlob.type}`
    );

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
    if (currentAudio) {
      currentAudio.pause();
    }
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  });
});
