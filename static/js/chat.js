// Mr. Easy Money Chat Widget
(function () {
    const WELCOME = "Hey there! I'm Mr. Easy Money. Ask me anything about budgeting, saving, investing, getting out of debt, or the Money Glow-Up course. No judgment, just real talk. Easy money, easy life! What's on your mind?";

    let messages = [];
    let isOpen = false;
    let isStreaming = false;

    // Build the widget DOM
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
                        <div class="text-black/70 text-xs">Your AI Finance Coach</div>
                    </div>
                </div>
                <button onclick="document.getElementById('chat-toggle').click()" class="text-black/70 hover:text-black transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                </button>
            </div>
            <div id="chat-messages" class="flex-1 overflow-y-auto p-4 space-y-3"></div>
            <div class="border-t border-gray-700 p-3 flex-shrink-0">
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

        // Form handler
        document.getElementById("chat-form").onsubmit = function (e) {
            e.preventDefault();
            sendMessage();
        };
    }

    function toggleChat() {
        isOpen = !isOpen;
        const panel = document.getElementById("chat-panel");
        const btn = document.getElementById("chat-toggle");
        if (isOpen) {
            panel.classList.remove("hidden");
            panel.classList.add("visible");
            btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>`;
            // Show welcome message on first open
            if (messages.length === 0) {
                addMessage("assistant", WELCOME);
            }
            document.getElementById("chat-input").focus();
        } else {
            panel.classList.remove("visible");
            panel.classList.add("hidden");
            btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>`;
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
        // Simple markdown: bold, line breaks, lists
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

        isStreaming = true;
        document.getElementById("chat-send").disabled = true;
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
                            if (e.message !== "Unexpected end of JSON input") {
                                console.error("Parse error:", e);
                            }
                        }
                    }
                }
            }

            messages.push({ role: "assistant", content: fullText });

            // Keep conversation manageable
            if (messages.length > 20) {
                messages = messages.slice(-20);
            }
        } catch (err) {
            removeTyping();
            addMessage("assistant", "Oops! Something went wrong on my end. Try again in a sec. If the chat isn't working, it might mean the AI service is being set up. Check back soon!");
            console.error("Chat error:", err);
        } finally {
            isStreaming = false;
            document.getElementById("chat-send").disabled = false;
            document.getElementById("chat-input").focus();
        }
    }

    // Init
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", createWidget);
    } else {
        createWidget();
    }
})();
