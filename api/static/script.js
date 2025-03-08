let currentVideoId = null;
let loadingContent = false;

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
    
    // Enable tabs
    document.querySelectorAll('.tab-button').forEach(button => {
        button.disabled = false;
    });
    
    // Load content once
    await loadTranscriptAndSummary(videoId);
    
    // Switch to first available tab
    switchTab('summary');
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

async function loadTranscriptAndSummary(videoId) {
    // Highlight selected video
    highlightSelectedVideo(videoId);
    
    try {
        // Load both transcript and summary
        const [transcriptResponse, summaryResponse] = await Promise.all([
            fetch(`/transcript/${videoId}`),
            fetch(`/summary/${videoId}`)
        ]);

        // Check response status before trying to parse JSON
        if (!transcriptResponse.ok || !summaryResponse.ok) {
            let errorMessage = '';
            if (!transcriptResponse.ok) {
                errorMessage += `Transcript error: ${transcriptResponse.status} ${transcriptResponse.statusText}\n`;
            }
            if (!summaryResponse.ok) {
                errorMessage += `Summary error: ${summaryResponse.status} ${summaryResponse.statusText}`;
            }
            throw new Error(errorMessage);
        }

        // Parse JSON responses
        const [transcriptData, summaryData] = await Promise.all([
            transcriptResponse.json(),
            summaryResponse.json()
        ]);

        // Update transcript tab
        const transcriptContent = document.getElementById('transcript-content');
        if (transcriptData.error) {
            transcriptContent.innerHTML = `<p class="text-red-500">${transcriptData.error}</p>`;
        } else {
            transcriptContent.innerHTML = marked.parse(transcriptData.content || '');
        }

        // Update summary tab
        const summaryContent = document.getElementById('summary-content');
        if (summaryData.error) {
            summaryContent.innerHTML = `<p class="text-red-500">${summaryData.error}</p>`;
        } else if (summaryData.content) {
            summaryContent.innerHTML = marked.parse(summaryData.content);
        } else {
            summaryContent.innerHTML = '<p class="text-gray-500">No summary available</p>';
        }
    } catch (error) {
        console.error('Error loading content:', error);
        const errorMessage = error.message || 'Failed to load content';
        document.getElementById('transcript-content').innerHTML = `<p class="text-red-500">${errorMessage}</p>`;
        document.getElementById('summary-content').innerHTML = `<p class="text-red-500">${errorMessage}</p>`;
    }
}

function sendMessage() {
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
            const data = await response.json();
            
            if (data.status === 'success') {
                alert('Notes saved successfully!');
            } else {
                alert('Error saving notes: ' + data.message);
            }
        } catch (error) {
            console.error('Error saving notes:', error);
            alert('Error saving notes. Please try again.');
        }
    } else {
        alert('Please select a video first.');
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
        alert('Please enter a YouTube URL');
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
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
        } else {
            // Refresh the page to show the new video
            window.location.reload();
        }
    } catch (error) {
        alert('Error processing video: ' + error);
    } finally {
        // Re-enable the input and button
        urlInput.disabled = false;
        button.disabled = false;
        button.innerHTML = originalButtonContent;
    }
}

async function deleteVideo(videoId, event) {
    // Prevent the click from bubbling up to the parent
    event.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this video? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/delete-video/${videoId}`, {
            method: 'DELETE'
        });

        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
        } else {
            // Get the video element using data-video-id attribute
            const videoElement = document.querySelector(`[data-video-id="${videoId}"]`);
            if (videoElement) {
                videoElement.remove();
            } else {
                console.error('Could not find video element to remove');
            }
        }
    } catch (error) {
        alert('Error deleting video: ' + error);
    }
}

async function changeSort(sortBy) {
    try {
        const response = await fetch(`/?sort=${sortBy}`);
        const html = await response.text();
        
        // Extract the video list content from the response
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Add debug logging
        console.log('Available classes:', doc.querySelector('.video-list-content'));
        
        const newVideoList = doc.querySelector('.video-list-content');
        if (!newVideoList) {
            console.error('Could not find video list content in response');
            return;
        }
        
        // Update the current video list
        const currentList = document.querySelector('.video-list-content');
        if (!currentList) {
            console.error('Could not find current video list');
            return;
        }
        
        currentList.innerHTML = newVideoList.innerHTML;
    } catch (error) {
        console.error('Error changing sort:', error);
        alert('Error updating the video list. Please refresh the page and try again.');
    }
}

// Initialize event listeners when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Allow Enter key to send message
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    // Add event listener for Enter key in YouTube URL input
    const urlInput = document.getElementById('youtube-url-input');
    if (urlInput) {
        urlInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                processVideo();
            }
        });
    }

    // Config modal functionality
    const configButton = document.getElementById('config-button');
    const configModal = document.getElementById('config-modal');
    const closeConfigModal = document.getElementById('close-config-modal');
    const configEditor = document.getElementById('config-editor');
    const saveConfigButton = document.getElementById('save-config-button');

    if (configButton && configModal) {
        // Open config modal
        configButton.addEventListener('click', async function() {
            try {
                const response = await fetch('/config');
                const data = await response.json();
                
                if (data.error) {
                    alert('Error loading configuration: ' + data.error);
                    return;
                }
                
                // Format JSON for better readability
                try {
                    const jsonObj = JSON.parse(data.content);
                    configEditor.value = JSON.stringify(jsonObj, null, 4);
                } catch (e) {
                    configEditor.value = data.content;
                }
                
                configModal.classList.remove('hidden');
            } catch (error) {
                alert('Error loading configuration: ' + error);
            }
        });

        // Close config modal
        closeConfigModal.addEventListener('click', function() {
            configModal.classList.add('hidden');
        });

        // Save config
        saveConfigButton.addEventListener('click', async function() {
            try {
                // Validate JSON
                try {
                    JSON.parse(configEditor.value);
                } catch (e) {
                    alert('Invalid JSON: ' + e.message);
                    return;
                }
                
                const response = await fetch('/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ content: configEditor.value }),
                });
                
                const data = await response.json();
                
                if (data.error) {
                    alert('Error saving configuration: ' + data.error);
                } else {
                    alert('Configuration saved successfully!');
                    configModal.classList.add('hidden');
                }
            } catch (error) {
                alert('Error saving configuration: ' + error);
            }
        });

        // Close modal when clicking outside
        configModal.addEventListener('click', function(event) {
            if (event.target === configModal) {
                configModal.classList.add('hidden');
            }
        });
    }

    // Initialize marked
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true
        });
    }
});
