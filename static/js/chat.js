// Mr. Easy Money Chat Widget — with Server-Side Voice Mode
(function () {
    const WELCOME = "Hey there! I'm Mr. Easy Money. Ask me anything about budgeting, saving, investing, getting out of debt, or the Money Glow-Up course. No judgment, just real talk. Easy money, easy life! What's on your mind?";

    let messages = [];
    let isOpen = false;
    let isStreaming = false;
    let voiceMode = false;
    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    // No browser Speech Synthesis — all TTS via Gemini server

    // Voice is available if browser supports MediaRecorder (virtually all modern browsers)
    const hasVoice = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);

    function createWidget() {
        // Floating button
        const btn = document.createElement("button");
        btn.id = "chat-toggle";
        btn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>`;
        btn.className = "fixed bottom-6 right-6 z-50 w-16 h-16 rounded-full gold-gradient text-black shadow-2xl flex items-center justify-center cursor-pointer hover:scale-110 transition-transform pulse-gold";
        btn.onclick = toggleChat;
        document.body.appendChild(btn);

        // Chat panel
        const panel = document.createElement("div");
        panel.id = "chat-panel";
        panel.className = "chat-panel hidden fixed bottom-24 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden";
        panel.style.height = "520px";
        panel.innerHTML = `
            <div class="bg-gradient-to-r from-amber-500 to-emerald-500 px-4 py-3 flex items-center justify-between flex-shrink-0">
                <div class="flex items-center gap-2">
                    <span class="text-2xl">&#128176;</span>
                    <div>
                        <div class="font-bold text-black text-sm">Mr. Easy Money</div>
                        <div class="text-black/70 text-xs" id="chat-subtitle">Your AI Finance Coach</div>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    ${hasVoice ? `<button id="voice-toggle" onclick="window.__mrem_toggleVoice()" class="text-black/70 hover:text-black transition-colors" title="Toggle voice mode">
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                        </svg>
                    </button>` : ''}
                    <button onclick="document.getElementById('chat-toggle').click()" class="text-black/70 hover:text-black transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                </div>
            </div>
            <div id="chat-messages" class="flex-1 overflow-y-auto p-4 space-y-3"></div>
            <!-- Voice mode area (hidden by default) -->
            <div id="voice-visualizer" class="hidden border-t border-gray-700 p-4 flex-shrink-0">
                <div class="flex flex-col items-center gap-3">
                    <div id="voice-waves" class="flex items-center gap-1 h-8">
                        <div class="voice-bar w-1 bg-amber-500 rounded-full" style="height:8px"></div>
                        <div class="voice-bar w-1 bg-amber-400 rounded-full" style="height:12px"></div>
                        <div class="voice-bar w-1 bg-emerald-500 rounded-full" style="height:16px"></div>
                        <div class="voice-bar w-1 bg-emerald-400 rounded-full" style="height:20px"></div>
                        <div class="voice-bar w-1 bg-amber-500 rounded-full" style="height:24px"></div>
                        <div class="voice-bar w-1 bg-amber-400 rounded-full" style="height:16px"></div>
                        <div class="voice-bar w-1 bg-emerald-500 rounded-full" style="height:12px"></div>
                        <div class="voice-bar w-1 bg-emerald-400 rounded-full" style="height:8px"></div>
                    </div>
                    <div id="voice-status" class="text-gray-400 text-xs">Tap mic to talk &bull; Tap again to send</div>
                    <button id="mic-btn" onclick="window.__mrem_toggleMic()" class="w-14 h-14 rounded-full bg-gray-800 border-2 border-gray-600 flex items-center justify-center hover:border-amber-500 transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                        </svg>
                    </button>
                </div>
            </div>
            <!-- Text input (shown by default) -->
            <div id="text-input-area" class="border-t border-gray-700 p-3 flex-shrink-0">
                <form id="chat-form" class="flex gap-2">
                    <input id="chat-input" type="text" placeholder="Ask me anything about money..."
                        class="flex-1 bg-gray-800 text-white rounded-lg px-4 py-2 text-sm border border-gray-600 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 placeholder-gray-400" />
                    <button type="submit" id="chat-send"
                        class="bg-amber-500 hover:bg-amber-400 text-black font-bold rounded-lg px-4 py-2 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                        Send
                    </button>
                </form>
            </div>`;
        document.body.appendChild(panel);

        document.getElementById("chat-form").onsubmit = function (e) {
            e.preventDefault();
            sendMessage();
        };
    }

    // ========== Voice Controls ==========

    window.__mrem_toggleVoice = function () {
        voiceMode = !voiceMode;
        const voiceVis = document.getElementById("voice-visualizer");
        const textArea = document.getElementById("text-input-area");
        const voiceBtn = document.getElementById("voice-toggle");
        const subtitle = document.getElementById("chat-subtitle");

        if (voiceMode) {
            voiceVis.classList.remove("hidden");
            textArea.classList.add("hidden");
            voiceBtn.classList.add("bg-black/20", "rounded-lg");
            subtitle.textContent = "Voice Mode Active";
        } else {
            voiceVis.classList.add("hidden");
            textArea.classList.remove("hidden");
            voiceBtn.classList.remove("bg-black/20", "rounded-lg");
            subtitle.textContent = "Your AI Finance Coach";
            if (isRecording) stopRecording(true); // discard
        }
    };

    window.__mrem_toggleMic = function () {
        if (isStreaming) return;
        if (isRecording) {
            stopRecording(false); // stop and send
        } else {
            startRecording();
        }
    };

    async function startRecording() {
        if (isStreaming) return;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];

            // Try webm first, fall back to other formats
            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus"
                : MediaRecorder.isTypeSupported("audio/webm")
                    ? "audio/webm"
                    : "";

            mediaRecorder = mimeType
                ? new MediaRecorder(stream, { mimeType })
                : new MediaRecorder(stream);

            mediaRecorder.ondataavailable = function (e) {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = function () {
                // Stop all tracks to release the mic
                stream.getTracks().forEach(t => t.stop());
            };

            mediaRecorder.start(100); // collect chunks every 100ms
            isRecording = true;

            const micBtn = document.getElementById("mic-btn");
            micBtn.classList.add("border-red-500", "bg-red-500/20");
            micBtn.classList.remove("border-gray-600", "bg-gray-800");
            document.getElementById("voice-status").textContent = "Recording... Tap mic to send";
            animateVoiceBars(true);
        } catch (err) {
            console.error("Mic error:", err);
            document.getElementById("voice-status").textContent =
                err.name === "NotAllowedError"
                    ? "Mic access denied. Check browser permissions."
                    : "Mic error. Please try again.";
        }
    }

    function stopRecording(discard) {
        if (!mediaRecorder || mediaRecorder.state === "inactive") return;

        isRecording = false;
        const micBtn = document.getElementById("mic-btn");
        micBtn.classList.remove("border-red-500", "bg-red-500/20");
        micBtn.classList.add("border-gray-600", "bg-gray-800");
        animateVoiceBars(false);

        if (discard) {
            mediaRecorder.stop();
            document.getElementById("voice-status").textContent = "Tap mic to talk";
            return;
        }

        // Wait for final data then send
        mediaRecorder.onstop = function () {
            // Release mic
            if (mediaRecorder.stream) {
                mediaRecorder.stream.getTracks().forEach(t => t.stop());
            }
            if (audioChunks.length === 0) {
                document.getElementById("voice-status").textContent = "No audio captured. Try again.";
                return;
            }
            const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
            sendVoice(audioBlob);
        };
        mediaRecorder.stop();
        document.getElementById("voice-status").textContent = "Processing...";
    }

    async function sendVoice(audioBlob) {
        isStreaming = true;
        animateVoiceBars(true);
        document.getElementById("voice-status").textContent = "Transcribing...";
        console.log("[Voice] Sending audio:", audioBlob.size, "bytes, type:", audioBlob.type);

        try {
            const formData = new FormData();
            formData.append("audio", audioBlob, "voice.webm");
            formData.append("history", JSON.stringify(messages));

            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 60000); // 60s timeout

            document.getElementById("voice-status").textContent = "Thinking...";
            const res = await fetch("/api/voice", {
                method: "POST",
                body: formData,
                signal: controller.signal,
            });
            clearTimeout(timeout);

            console.log("[Voice] Response status:", res.status);
            const data = await res.json();
            console.log("[Voice] Got response:", data.user_text?.substring(0, 50), "| audio:", !!data.audio);

            if (!res.ok) {
                throw new Error(data.error || "Voice chat failed");
            }

            // Show transcribed user text
            addMessage("user", data.user_text);
            messages.push({ role: "user", content: data.user_text });

            // Show assistant response immediately
            addMessage("assistant", data.assistant_text);
            messages.push({ role: "assistant", content: data.assistant_text });

            if (messages.length > 20) messages = messages.slice(-20);

            // Fetch TTS audio separately (non-blocking)
            document.getElementById("voice-status").textContent = "Generating voice...";
            fetchAndPlayTTS(data.assistant_text);

        } catch (err) {
            console.error("Voice error:", err);
            document.getElementById("voice-status").textContent = "Error: " + err.message;
            animateVoiceBars(false);
        } finally {
            isStreaming = false;
        }
    }

    let currentAudio = null; // Track current playing audio

    async function fetchAndPlayTTS(text) {
        // Stop any currently playing audio
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }

        document.getElementById("voice-status").textContent = "Generating voice...";
        animateVoiceBars(true);
        console.log("[Voice] Fetching TTS for:", text.substring(0, 60) + "...");

        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 120000);

            const res = await fetch("/api/tts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text }),
                signal: controller.signal,
            });
            clearTimeout(timeout);

            if (!res.ok) {
                const errText = await res.text();
                console.log("[Voice] TTS failed:", res.status, errText);
                document.getElementById("voice-status").textContent = "Voice unavailable. Tap mic to talk.";
                animateVoiceBars(false);
                return;
            }

            const blob = await res.blob();
            console.log("[Voice] Got TTS audio:", blob.size, "bytes, type:", blob.type);

            // Decode into AudioContext for more reliable playback
            const arrayBuf = await blob.arrayBuffer();
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const audioBuffer = await audioCtx.decodeAudioData(arrayBuf);

            console.log("[Voice] Decoded audio:", audioBuffer.duration.toFixed(1) + "s", audioBuffer.sampleRate + "Hz");

            document.getElementById("voice-status").textContent = "Speaking...";

            const source = audioCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioCtx.destination);

            currentAudio = { pause: () => { try { source.stop(); } catch(e) {} audioCtx.close(); } };

            source.onended = function () {
                currentAudio = null;
                audioCtx.close();
                document.getElementById("voice-status").textContent = "Tap mic to talk";
                animateVoiceBars(false);
                console.log("[Voice] Playback complete");
            };

            source.start(0);
            console.log("[Voice] Playback started");

        } catch (err) {
            console.log("[Voice] TTS error:", err);
            document.getElementById("voice-status").textContent = err.name === "AbortError"
                ? "Voice timed out. Tap mic to talk."
                : "Voice error. Tap mic to talk.";
            animateVoiceBars(false);
        }
    }

    // ========== Voice Bars Animation ==========

    let barInterval = null;
    function animateVoiceBars(active) {
        const bars = document.querySelectorAll(".voice-bar");
        if (barInterval) clearInterval(barInterval);
        if (active) {
            barInterval = setInterval(() => {
                bars.forEach(bar => {
                    bar.style.height = (4 + Math.random() * 28) + "px";
                    bar.style.transition = "height 0.1s ease";
                });
            }, 100);
        } else {
            bars.forEach((bar, i) => {
                bar.style.height = [8, 12, 16, 20, 24, 16, 12, 8][i] + "px";
                bar.style.transition = "height 0.3s ease";
            });
        }
    }

    // All TTS handled by fetchAndPlayTTS() via Gemini server — no browser Speech Synthesis

    // ========== Chat Core ==========

    function toggleChat() {
        isOpen = !isOpen;
        const panel = document.getElementById("chat-panel");
        const btn = document.getElementById("chat-toggle");
        if (isOpen) {
            panel.classList.remove("hidden");
            panel.classList.add("visible");
            btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>`;
            if (messages.length === 0) addMessage("assistant", WELCOME);
            if (!voiceMode) document.getElementById("chat-input").focus();
        } else {
            panel.classList.remove("visible");
            panel.classList.add("hidden");
            btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>`;
            if (isRecording) stopRecording(true);
        }
    }

    function addMessage(role, text) {
        const container = document.getElementById("chat-messages");
        const wrapper = document.createElement("div");
        wrapper.className = role === "user" ? "flex justify-end" : "flex justify-start";
        const bubble = document.createElement("div");
        bubble.className = role === "user"
            ? "bg-amber-500 text-black rounded-2xl rounded-br-md px-4 py-2 max-w-[80%] text-sm"
            : "bg-gray-800 text-gray-100 rounded-2xl rounded-bl-md px-4 py-2 max-w-[80%] text-sm chat-msg";
        bubble.innerHTML = formatMarkdown(text);
        wrapper.appendChild(bubble);
        container.appendChild(wrapper);
        container.scrollTop = container.scrollHeight;
        return bubble;
    }

    function showTyping() {
        const container = document.getElementById("chat-messages");
        const wrapper = document.createElement("div");
        wrapper.className = "flex justify-start";
        wrapper.id = "typing-indicator";
        const bubble = document.createElement("div");
        bubble.className = "bg-gray-800 rounded-2xl rounded-bl-md px-4 py-3";
        bubble.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
        wrapper.appendChild(bubble);
        container.appendChild(wrapper);
        container.scrollTop = container.scrollHeight;
    }

    function removeTyping() {
        const el = document.getElementById("typing-indicator");
        if (el) el.remove();
    }

    function formatMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\n- /g, "<br>&bull; ")
            .replace(/\n\d+\. /g, function (m) { return "<br>" + m.trim() + " "; })
            .replace(/\n/g, "<br>");
    }

    async function sendMessage() {
        if (isStreaming) return;
        const input = document.getElementById("chat-input");
        const text = input.value.trim();
        if (!text) return;

        input.value = "";
        addMessage("user", text);
        messages.push({ role: "user", content: text });
        await streamResponse();
    }

    async function streamResponse() {
        isStreaming = true;
        const sendBtn = document.getElementById("chat-send");
        if (sendBtn) sendBtn.disabled = true;
        showTyping();

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ messages: messages }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || "Chat unavailable");
            }

            removeTyping();
            const bubble = addMessage("assistant", "");
            let fullText = "";

            const reader = res.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n");
                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const data = line.slice(6);
                        if (data === "[DONE]") break;
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.error) throw new Error(parsed.error);
                            if (parsed.text) {
                                fullText += parsed.text;
                                bubble.innerHTML = formatMarkdown(fullText);
                                document.getElementById("chat-messages").scrollTop =
                                    document.getElementById("chat-messages").scrollHeight;
                            }
                        } catch (e) {
                            if (e.message !== "Unexpected end of JSON input") console.error("Parse error:", e);
                        }
                    }
                }
            }

            messages.push({ role: "assistant", content: fullText });
            if (messages.length > 20) messages = messages.slice(-20);

            // If voice mode is on, fetch TTS for the text response too
            if (voiceMode) fetchAndPlayTTS(fullText);

        } catch (err) {
            removeTyping();
            addMessage("assistant", "Oops! Something went wrong. Try again in a sec.");
            console.error("Chat error:", err);
        } finally {
            isStreaming = false;
            const sendBtn = document.getElementById("chat-send");
            if (sendBtn) sendBtn.disabled = false;
            if (!voiceMode) {
                const inp = document.getElementById("chat-input");
                if (inp) inp.focus();
            }
        }
    }

    // Init
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", createWidget);
    } else {
        createWidget();
    }
})();
