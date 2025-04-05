let currentVideoId = null;
let loadingContent = false;

// Function to show flash messages
function showFlashMessage(message, category = 'success') {
    const flashContainer = document.getElementById('flash-messages');
    const messageDiv = document.createElement('div');
    
    let bgColor, textColor, borderColor;
    if (category === 'error') {
        bgColor = 'bg-red-100';
        textColor = 'text-red-700';
        borderColor = 'border-red-400';
    } else if (category === 'warning') {
        bgColor = 'bg-yellow-100';
        textColor = 'text-yellow-700';
        borderColor = 'border-yellow-400';
    } else {
        bgColor = 'bg-green-100';
        textColor = 'text-green-700';
        borderColor = 'border-green-400';
    }
    
    messageDiv.className = `mb-4 p-4 rounded ${bgColor} ${textColor} border ${borderColor}`;
    messageDiv.textContent = message;
    
    flashContainer.appendChild(messageDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab
    const selectedTab = document.getElementById(`${tabName}-tab`);
    selectedTab.classList.add('active');
    
    // Add active class to clicked button
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
}

async function selectVideo(videoId) {
    if (currentVideoId === videoId) {
        console.log('Video already selected:', videoId);
        return;
    }
    
    console.log('Selecting video:', videoId);
    currentVideoId = videoId;
    
    // Highlight selected video
    highlightSelectedVideo(videoId);
    
    // Load content
    await loadVideoContent(videoId);
}

function highlightSelectedVideo(videoId) {
    // Remove highlight from all videos
    document.querySelectorAll('.video-list-content > div').forEach(el => {
        el.classList.remove('video-selected');
    });
    
    // Add highlight to selected video using the data-video-id attribute
    const selectedVideo = document.querySelector(`[data-video-id="${videoId}"]`);
    if (selectedVideo) {
        selectedVideo.classList.add('video-selected');
    } else {
        console.error('Could not find video element with ID:', videoId);
    }
}

async function loadVideoContent(videoId) {
    try {
        // Load video content (transcript, summary, script)
        const response = await fetch(`/video-content/${videoId}`);
        
        if (!response.ok) {
            throw new Error(`Error loading content: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Create content display
        const videoContent = document.getElementById('video-content');
        
        // Create tabs
        const tabsHtml = `
            <div class="flex border-b mb-4">
                <button onclick="switchTab('summary')" class="tab-button active" data-tab="summary">Summary</button>
                <button onclick="switchTab('transcript')" class="tab-button" data-tab="transcript">Transcript</button>
                <button onclick="switchTab('script')" class="tab-button" data-tab="script">Script</button>
                <button onclick="switchTab('notes')" class="tab-button" data-tab="notes">Notes</button>
            </div>
        `;
        
        // Create tab content
        const tabContentHtml = `
            <div id="summary-tab" class="tab-content active">
                <div class="markdown-body">${data.summary.content ? marked.parse(data.summary.content) : '<p class="text-gray-500">No summary available</p>'}</div>
            </div>
            <div id="transcript-tab" class="tab-content">
                <div class="markdown-body">${data.transcript.content ? marked.parse(data.transcript.content) : '<p class="text-gray-500">No transcript available</p>'}</div>
            </div>
            <div id="script-tab" class="tab-content">
                <div class="markdown-body">Loading script...</div>
            </div>
            <div id="notes-tab" class="tab-content">
                <div class="flex flex-col h-full">
                    <textarea id="notes-editor" class="w-full h-full p-4 border rounded resize-none focus:outline-none focus:border-blue-500" placeholder="Enter your notes here..."></textarea>
                    <div class="mt-4 flex justify-end">
                        <button onclick="saveNotes()" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">Save Notes</button>
                    </div>
                </div>
            </div>
        `;
        
        // Update the video content
        videoContent.innerHTML = tabsHtml + tabContentHtml;
        
        // Load script separately
        loadScript(videoId);
        
    } catch (error) {
        console.error('Error loading content:', error);
        const videoContent = document.getElementById('video-content');
        videoContent.innerHTML = `<div class="text-red-500 p-4">Error loading content: ${error.message}</div>`;
    }
}

async function loadScript(videoId) {
    try {
        const response = await fetch(`/script/${videoId}`);
        
        if (!response.ok) {
            throw new Error(`Error loading script: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Update script tab
        const scriptContent = document.getElementById('script-tab').querySelector('.markdown-body');
        scriptContent.innerHTML = data.content ? marked.parse(data.content) : '<p class="text-gray-500">No script available</p>';
        
    } catch (error) {
        console.error('Error loading script:', error);
        const scriptContent = document.getElementById('script-tab').querySelector('.markdown-body');
        scriptContent.innerHTML = `<p class="text-red-500">Error loading script: ${error.message}</p>`;
    }
}

function toggleChat() {
    const chatWindow = document.getElementById('chat-window');
    const mainContent = document.querySelector('.main-content');
    
    if (chatWindow.classList.contains('active')) {
        chatWindow.classList.remove('active');
        mainContent.classList.remove('chat-active');
    } else {
        chatWindow.classList.add('active');
        mainContent.classList.add('chat-active');
    }
}

function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (message) {
        // Add message to chat
        const messagesDiv = document.getElementById('chat-messages');
        messagesDiv.innerHTML += `
            <div class="flex justify-end mb-4">
                <div class="bg-blue-100 rounded-lg px-4 py-2 max-w-[80%]">
                    ${message}
                </div>
            </div>
        `;
        // Clear input
        input.value = '';
        // Scroll to bottom
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

async function saveNotes() {
    const notes = document.getElementById('notes-editor').value;
    if (currentVideoId) {
        try {
            const response = await fetch(`/save-notes/${currentVideoId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ notes }),
            });
            
            if (!response.ok) {
                throw new Error(`Error saving notes: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                showFlashMessage('Notes saved successfully!');
            } else {
                showFlashMessage('Error saving notes: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('Error saving notes:', error);
            showFlashMessage('Error saving notes. Please try again.', 'error');
        }
    } else {
        showFlashMessage('Please select a video first.', 'warning');
    }
}

async function processVideo() {
    const urlInput = document.getElementById('youtube-url-input');
    if (!urlInput) {
        console.error('Could not find YouTube URL input element');
        return;
    }

    const url = urlInput.value.trim();
    
    if (!url) {
        showFlashMessage('Please enter a YouTube URL', 'warning');
        return;
    }

    // Disable the input and button during processing
    urlInput.disabled = true;
    const button = document.querySelector('button[onclick="processVideo()"]');
    const originalButtonContent = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `
        <svg class="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Processing...
    `;

    try {
        const response = await fetch('/process-video', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                url: url,
                force: true,
                transcribe: true,
                process: true,
                summarize: true
            })
        });

        if (!response.ok) {
            throw new Error(`Error processing video: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showFlashMessage(data.error, 'error');
        } else {
            // Add a temporary entry for the video being processed
            const videoId = data.video_id;
            
            // Create a new video element with processing status
            const videoInfo = {
                title: data.title || `Processing: ${videoId}`,
                channel: data.channel || 'Loading...',
                upload_date: data.upload_date || ''
            };
            addProcessingVideo(videoId, url, videoInfo);
            
            // Start polling for status updates
            startStatusPolling(videoId);
            
            // Clear the input field
            urlInput.value = '';
            
            showFlashMessage(`Video "${videoInfo.title}" added to processing queue.`);
        }
    } catch (error) {
        console.error('Error processing video:', error);
        showFlashMessage('Error processing video: ' + error.message, 'error');
    } finally {
        // Re-enable the input and button
        urlInput.disabled = false;
        button.disabled = false;
        button.innerHTML = originalButtonContent;
    }
}

function addProcessingVideo(videoId, url, videoInfo) {
    // Create a placeholder element for the processing video
    const videoElement = document.createElement('div');
    videoElement.className = 'bg-gray-200 rounded-lg shadow p-2 hover:bg-gray-200 cursor-pointer transition-colors';
    videoElement.setAttribute('data-video-id', videoId);
    videoElement.setAttribute('onclick', `selectVideo('${videoId}')`);
    
    // Format the upload date if available
    let formattedDate = '';
    if (videoInfo.upload_date) {
        try {
            const date = new Date(videoInfo.upload_date);
            formattedDate = date.toISOString().split('T')[0];
        } catch (e) {
            formattedDate = videoInfo.upload_date;
        }
    }
    
    // Create the video element content
    videoElement.innerHTML = `
        <div class="flex flex-col gap-1">
            <div class="text-base font-semibold hover:text-blue-600">
                <a href="https://www.youtube.com/watch?v=${videoId}" target="_blank">${videoInfo.title}</a>
            </div>
            <div class="flex items-center text-sm text-gray-600">
                <div class="flex-1">
                    ${videoInfo.channel} &nbsp;|&nbsp; ${formattedDate}
                </div>
                <div class="processing-indicator">
                    <svg class="animate-spin h-4 w-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span class="ml-2 text-blue-500">Processing</span>
                </div>
            </div>
        </div>
    `;
    
    // Add to the beginning of the video list
    const videoList = document.querySelector('.video-list-content');
    videoList.insertBefore(videoElement, videoList.firstChild);
}

function updateVideoStatus(videoId, status) {
    const videoElement = document.querySelector(`[data-video-id="${videoId}"]`);
    if (!videoElement) return;
    
    const statusIndicator = videoElement.querySelector('.processing-indicator');
    if (!statusIndicator) return;
    
    if (status === 'completed') {
        // Remove the processing indicator
        statusIndicator.remove();
        
        // Refresh the page to show the completed video
        window.location.reload();
    } else if (status === 'failed') {
        statusIndicator.innerHTML = `
            <svg class="h-4 w-4 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="ml-2 text-red-500">Failed</span>
        `;
    } else {
        statusIndicator.innerHTML = `
            <svg class="animate-spin h-4 w-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="ml-2 text-blue-500">${status}</span>
        `;
    }
}

function startStatusPolling(videoId) {
    // Poll for status updates every 5 seconds
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/video-status/${videoId}`);
            
            if (!response.ok) {
                throw new Error(`Error checking status: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            const status = data.status;
            
            updateVideoStatus(videoId, status);
            
            // Stop polling if processing is complete or failed
            if (status === 'completed' || status === 'failed') {
                clearInterval(pollInterval);
            }
        } catch (error) {
            console.error('Error polling status:', error);
            clearInterval(pollInterval);
        }
    }, 5000);
}

async function deleteVideo(videoId, event) {
    // Stop event propagation to prevent video selection
    event.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this video?')) {
        return;
    }
    
    try {
        const response = await fetch(`/delete-video/${videoId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`Error deleting video: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Remove the video element from the DOM
            const videoElement = document.querySelector(`[data-video-id="${videoId}"]`);
            if (videoElement) {
                videoElement.remove();
            }
            
            // If the deleted video was selected, clear the content area
            if (currentVideoId === videoId) {
                currentVideoId = null;
                document.getElementById('video-content').innerHTML = `
                    <div class="text-center text-gray-500 mt-20">
                        <svg class="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <p class="text-xl">Select a video to view its content</p>
                    </div>
                `;
            }
            
            showFlashMessage('Video deleted successfully');
        } else {
            showFlashMessage('Failed to delete video', 'error');
        }
    } catch (error) {
        console.error('Error deleting video:', error);
        showFlashMessage('Error deleting video: ' + error.message, 'error');
    }
}

async function changeSort(sortBy) {
    try {
        const response = await fetch(`/videos?sort=${sortBy}`);
        
        if (!response.ok) {
            throw new Error(`Error changing sort: ${response.status} ${response.statusText}`);
        }
        
        const html = await response.text();
        
        // Update the video list content
        const videoList = document.querySelector('.video-list-content');
        videoList.innerHTML = html;
        
        // Re-highlight the selected video if any
        if (currentVideoId) {
            highlightSelectedVideo(currentVideoId);
        }
    } catch (error) {
        console.error('Error changing sort:', error);
        showFlashMessage('Error changing sort: ' + error.message, 'error');
    }
}

// Config modal functions
function openConfigModal() {
    const modal = document.getElementById('config-modal');
    modal.classList.remove('hidden');
    
    // Load current config
    loadConfig();
}

function closeConfigModal() {
    const modal = document.getElementById('config-modal');
    modal.classList.add('hidden');
}

async function loadConfig() {
    try {
        const response = await fetch('/config');
        
        if (!response.ok) {
            throw new Error(`Error loading config: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Update the config editor
        const editor = document.getElementById('config-editor');
        editor.value = data.content;
    } catch (error) {
        console.error('Error loading config:', error);
        showFlashMessage('Error loading config: ' + error.message, 'error');
    }
}

async function saveConfig() {
    try {
        const editor = document.getElementById('config-editor');
        const content = editor.value;
        
        const response = await fetch('/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ content }),
        });
        
        if (!response.ok) {
            throw new Error(`Error saving config: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            showFlashMessage('Configuration saved successfully');
            closeConfigModal();
        } else {
            showFlashMessage('Failed to save configuration', 'error');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        showFlashMessage('Error saving config: ' + error.message, 'error');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Set up config button
    const configButton = document.getElementById('config-button');
    if (configButton) {
        configButton.addEventListener('click', openConfigModal);
    }
    
    // Set up chat toggle
    const chatToggleButton = document.querySelector('button[onclick="toggleChat()"]');
    if (chatToggleButton) {
        chatToggleButton.addEventListener('click', toggleChat);
    }

    // Add event listener for Enter key on URL input
    const urlInput = document.getElementById('youtube-url-input');
    if (urlInput) {
        urlInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent form submission
                processVideo();
            }
        });
    }
});
