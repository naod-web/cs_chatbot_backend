// components/layout/Chatbot/Chatbot.jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { Bot, X, Send, ThumbsUp, ThumbsDown, AlertCircle, RefreshCw, Volume2, VolumeX, ChevronUp, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from '@/components/ui/use-toast';
import { Slider } from '@/components/ui/slider';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5001/api/chatbot';

// Welcome audio base64 (lite "Welcome to Siket Bank" sound)
const WELCOME_AUDIO_BASE64 = '/home/gemechug/Downloads/bank-vault-100469.mp3'; // Placeholder - replace with actual sound

// Create simple beep tones for different sounds
const createBeepSound = (frequency = 440, duration = 0.3, volume = 0.3) => {
  try {
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContext) return () => {};
    
    return () => {
      const context = new AudioContext();
      const oscillator = context.createOscillator();
      const gainNode = context.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(context.destination);
      
      oscillator.frequency.value = frequency;
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(volume, context.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, context.currentTime + duration);
      
      oscillator.start(context.currentTime);
      oscillator.stop(context.currentTime + duration);
      
      // Clean up
      setTimeout(() => context.close(), duration * 1000 + 100);
    };
  } catch (error) {
    console.warn('Web Audio API not available:', error);
    return () => {};
  }
};

// Pre-defined sound generators
const SoundManager = {
  welcome: () => {
    try {
      // Try to play welcome sound from audio file first
      const audio = new Audio(WELCOME_AUDIO_BASE64);
      audio.volume = 0.5;
      audio.play().catch(() => {
        // Fallback to beep
        createBeepSound(523.25, 0.5, 0.3)(); // C5 note for welcome
      });
    } catch {
      createBeepSound(523.25, 0.5, 0.3)(); // C5 note for welcome
    }
  },
  
  open: () => createBeepSound(659.25, 0.2, 0.2)(), // E5
  close: () => createBeepSound(554.37, 0.2, 0.2)(), // C#5
  sent: () => createBeepSound(783.99, 0.1, 0.2)(), // G5
  received: () => createBeepSound(659.25, 0.2, 0.3)(), // E5
  error: () => createBeepSound(392.00, 0.3, 0.4)(), // G4
  click: () => createBeepSound(880.00, 0.05, 0.2)(), // A5
};

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [userInput, setUserInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('checking');
  const [retryCount, setRetryCount] = useState(0);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [volume, setVolume] = useState(0.5); // 0 to 1
  const [showVolumeControl, setShowVolumeControl] = useState(false);
  const scrollAreaRef = useRef(null);
  const volumeControlRef = useRef(null);

  // Play sound with current volume
  const playSound = useCallback((soundName) => {
    if (soundEnabled && SoundManager[soundName]) {
      // Adjust volume for the sound
      const originalVolume = volume;
      SoundManager[soundName]();
    }
  }, [soundEnabled, volume]);

  // Click outside volume control handler
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (volumeControlRef.current && !volumeControlRef.current.contains(event.target)) {
        setShowVolumeControl(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Initialize session and test connection
  useEffect(() => {
    const initializeChatbot = async () => {
      // Get or create session ID
      const storedSessionId = localStorage.getItem('chatbot_session_id');
      if (storedSessionId) {
        setSessionId(storedSessionId);
      } else {
        const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        setSessionId(newSessionId);
        localStorage.setItem('chatbot_session_id', newSessionId);
      }
      
      // Load preferences
      const soundPref = localStorage.getItem('chatbot_sound_enabled');
      if (soundPref !== null) {
        setSoundEnabled(soundPref === 'true');
      }
      
      const volumePref = localStorage.getItem('chatbot_volume');
      if (volumePref !== null) {
        setVolume(parseFloat(volumePref));
      }
      
      // Test connection
      await testConnection();
    };
    
    initializeChatbot();
  }, []);

  // Play welcome sound when chatbot opens for first time
  useEffect(() => {
    if (isOpen && chatHistory.length === 0 && connectionStatus === 'connected') {
      setTimeout(() => {
        playSound('welcome');
      }, 300);
    }
  }, [isOpen, chatHistory.length, connectionStatus, playSound]);

  // Handle chatbot open/close with sounds
  const handleToggleChatbot = () => {
    if (isOpen) {
      playSound('close');
      setIsOpen(false);
      setShowVolumeControl(false);
    } else {
      playSound('open');
      setIsOpen(true);
    }
  };

  // Toggle sound on/off
  const toggleSound = () => {
    const newSoundState = !soundEnabled;
    setSoundEnabled(newSoundState);
    localStorage.setItem('chatbot_sound_enabled', newSoundState.toString());
    
    // Play click sound when toggling
    if (newSoundState) {
      playSound('click');
    }
    
    toast({
      title: newSoundState ? "🔊 Sounds Enabled" : "🔇 Sounds Disabled",
      description: newSoundState ? "Chatbot sounds are now active" : "Chatbot sounds are now muted",
      duration: 2000,
    });
  };

  // Update volume
  const updateVolume = (newVolume) => {
    setVolume(newVolume);
    localStorage.setItem('chatbot_volume', newVolume.toString());
    
    // Play test sound when adjusting volume
    if (soundEnabled) {
      playSound('click');
    }
  };

  // Increase volume
  const increaseVolume = () => {
    const newVolume = Math.min(1, volume + 0.1);
    updateVolume(newVolume);
  };

  // Decrease volume
  const decreaseVolume = () => {
    const newVolume = Math.max(0, volume - 0.1);
    updateVolume(newVolume);
  };

  // Test backend connection
  const testConnection = async () => {
    setConnectionStatus('checking');
    try {
      const response = await axios.get(`${API_BASE_URL}/health`, { 
        timeout: 5000,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (response.data && response.data.status === 'healthy') {
        setConnectionStatus('connected');
        setRetryCount(0);
        return true;
      } else {
        setConnectionStatus('disconnected');
        return false;
      }
    } catch (error) {
      console.error('Connection test failed:', error);
      setConnectionStatus('disconnected');
      
      // Auto-retry logic
      if (retryCount < 3) {
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          testConnection();
        }, 2000);
      }
      return false;
    }
  };

  // Scroll to bottom of chat
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        setTimeout(() => {
          scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }, 100);
      }
    }
  }, [chatHistory, isLoading]);

  // Load initial greeting when opened and connected
  useEffect(() => {
    if (isOpen && chatHistory.length === 0 && connectionStatus === 'connected') {
      setChatHistory([
        {
          id: 'welcome_' + Date.now(),
          type: 'bot',
          message: 'Hello! Welcome to SiketBank. I am your AI assistant. How can I help you today?',
          timestamp: new Date().toISOString(),
          suggestions: [
            'Check account balance',
            'Loan information',
            'Branch locations',
            'Customer support',
            'Online banking'
          ]
        }
      ]);
    }
  }, [isOpen, connectionStatus]);

  // Get customer ID from auth context or localStorage
  const getCustomerId = () => {
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      return user.id || user.customerId || user.email || 'guest_' + Math.random().toString(36).substr(2, 6);
    } catch {
      return 'guest_' + Math.random().toString(36).substr(2, 6);
    }
  };

  // Handle sending message
  const handleSendMessage = async () => {
    if (!userInput.trim() || isLoading || connectionStatus !== 'connected') return;

    const message = userInput.trim();
    const customerId = getCustomerId();

    // Add user message to chat
    const userMessage = {
      id: 'user_' + Date.now(),
      type: 'user',
      message: message,
      timestamp: new Date().toISOString()
    };

    setChatHistory(prev => [...prev, userMessage]);
    setUserInput('');
    setIsLoading(true);
    
    // Play message sent sound
    playSound('sent');

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: message,
        session_id: sessionId,
        customer_id: customerId,
        context: {}
      }, {
        timeout: 15000,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });

      if (response.data.success) {
        const responseData = response.data.data;
        
        const botResponse = {
          id: 'bot_' + Date.now(),
          type: 'bot',
          message: responseData.response || "I received your message but couldn't generate a proper response.",
          intent: responseData.intent || 'unknown',
          confidence: responseData.confidence || 0,
          suggestions: responseData.suggestions || [],
          log_id: responseData.log_id,
          timestamp: responseData.timestamp || new Date().toISOString()
        };

        setChatHistory(prev => [...prev, botResponse]);
        
        // Play message received sound
        setTimeout(() => {
          playSound('received');
        }, 300);
        
      } else {
        const errorResponse = {
          id: 'error_' + Date.now(),
          type: 'bot',
          message: response.data.error || "I'm having trouble responding. Please try again.",
          isError: true,
          timestamp: new Date().toISOString()
        };
        setChatHistory(prev => [...prev, errorResponse]);
        playSound('error');
      }
    } catch (error) {
      console.error('Chatbot API error:', error);
      
      let errorMessage = "Unable to connect to chatbot service. ";
      
      if (error.code === 'ECONNABORTED') {
        errorMessage += "Request timed out. Please try again.";
      } else if (error.response) {
        errorMessage += `Server error: ${error.response.status}`;
        if (error.response.data?.error) {
          errorMessage += ` - ${error.response.data.error}`;
        }
      } else if (error.request) {
        errorMessage += "No response from server. Please check if the backend is running on port 5001.";
        setConnectionStatus('disconnected');
      } else {
        errorMessage += error.message;
      }
      
      const errorResponse = {
        id: 'error_' + Date.now(),
        type: 'bot',
        message: errorMessage,
        isError: true,
        timestamp: new Date().toISOString()
      };
      setChatHistory(prev => [...prev, errorResponse]);
      
      // Play error sound
      playSound('error');
      
      // Show toast notification
      toast({
        title: "Connection Error",
        description: "Failed to connect to chatbot service",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle key press (Enter to send)
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Handle suggestion click
  const handleSuggestionClick = (suggestion) => {
    setUserInput(suggestion);
    // Auto-send after short delay
    setTimeout(() => {
      if (connectionStatus === 'connected') {
        handleSendMessage();
      }
    }, 100);
  };

  // Handle feedback
  const handleFeedback = async (logId, rating) => {
    if (!logId) {
      toast({
        title: "Feedback Error",
        description: "No log ID available for feedback",
        variant: "destructive",
      });
      return;
    }
    
    try {
      const response = await axios.post(`${API_BASE_URL}/feedback`, {
        log_id: logId,
        rating: rating,
        comments: 'User feedback from web interface'
      }, {
        timeout: 5000
      });
      
      if (response.data.success) {
        toast({
          title: "Thank You!",
          description: "Your feedback has been submitted.",
        });
      } else {
        toast({
          title: "Feedback Failed",
          description: response.data.error || "Failed to submit feedback",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      toast({
        title: "Feedback Error",
        description: "Unable to submit feedback",
        variant: "destructive",
      });
    }
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'Just now';
    }
  };

  // Reset chat and start new session
  const resetChat = async () => {
    const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    setSessionId(newSessionId);
    localStorage.setItem('chatbot_session_id', newSessionId);
    setChatHistory([]);
    
    // Play welcome sound for new chat
    playSound('welcome');
    
    // Test connection after reset
    await testConnection();
    
    toast({
      title: "New Chat Started",
      description: "New session has been created",
    });
  };

  // Get status color and icon
  const getStatusInfo = () => {
    switch (connectionStatus) {
      case 'connected':
        return { 
          color: 'bg-green-500', 
          text: 'Online',
          icon: <Bot className="h-5 w-5" /> 
        };
      case 'disconnected':
        return { 
          color: 'bg-red-500', 
          text: 'Offline',
          icon: <AlertCircle className="h-5 w-5" /> 
        };
      case 'checking':
        return { 
          color: 'bg-yellow-500', 
          text: 'Connecting...',
          icon: <RefreshCw className="h-5 w-5 animate-spin" /> 
        };
      default:
        return { 
          color: 'bg-gray-500', 
          text: 'Unknown',
          icon: <AlertCircle className="h-5 w-5" /> 
        };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Chatbot Toggle Button */}
      <Button
        className={`h-14 w-14 rounded-full shadow-lg transition-all duration-300 ${
          isOpen 
            ? 'bg-red-500 hover:bg-red-600' 
            : statusInfo.color.replace('bg-', 'bg-')
        }`}
        onClick={handleToggleChatbot}
      >
        {isOpen ? (
          <X className="h-6 w-6 text-white" />
        ) : (
          statusInfo.icon
        )}
      </Button>

      {/* Online Status Indicator */}
      <div className={`absolute -top-2 -right-2 h-6 w-6 rounded-full border-2 border-white flex items-center justify-center ${
        connectionStatus === 'connected' 
          ? 'bg-green-500' 
          : connectionStatus === 'checking'
          ? 'bg-yellow-500 animate-pulse'
          : 'bg-red-500'
      }`}>
        <div className={`h-2 w-2 rounded-full ${connectionStatus === 'connected' ? 'bg-white' : 'bg-transparent'}`} />
      </div>

      {/* Chatbot Window */}
      {isOpen && (
        <div className="absolute bottom-16 right-0 w-96 h-[600px] bg-white rounded-lg shadow-2xl border border-gray-200 flex flex-col">
          {/* Header */}
          <div className={`p-4 border-b rounded-t-lg ${
            connectionStatus === 'connected' 
              ? 'bg-gradient-to-r from-green-600 to-green-700' 
              : connectionStatus === 'checking'
              ? 'bg-gradient-to-r from-yellow-500 to-yellow-600'
              : 'bg-gradient-to-r from-red-600 to-red-700'
          } text-white`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`h-10 w-10 rounded-full flex items-center justify-center ${
                  connectionStatus === 'connected' 
                    ? 'bg-white/20' 
                    : 'bg-white/10'
                }`}>
                  {statusInfo.icon}
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="font-bold text-lg">SiketBank Assistant</h3>
                    <div className="flex items-center">
                      <div className={`h-2 w-2 rounded-full mr-1 ${
                        connectionStatus === 'connected' 
                          ? 'bg-green-300 animate-pulse' 
                          : connectionStatus === 'checking'
                          ? 'bg-yellow-300 animate-pulse'
                          : 'bg-red-300'
                      }`} />
                      <span className="text-xs opacity-90">
                        {connectionStatus === 'connected' 
                          ? 'AI powered banking assist' 
                          : statusInfo.text}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-white/80">
                    {connectionStatus === 'connected' 
                      ? 'Ready to help you with banking queries' 
                      : connectionStatus === 'checking'
                      ? 'Establishing connection...'
                      : 'Service unavailable'
                    }
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {/* Volume Control Area */}
                <div className="relative" ref={volumeControlRef}>
                  <div className="flex items-center space-x-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={toggleSound}
                      title={soundEnabled ? "Mute sounds" : "Unmute sounds"}
                    >
                      {soundEnabled ? (
                        <Volume2 className="h-4 w-4" />
                      ) : (
                        <VolumeX className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={() => setShowVolumeControl(!showVolumeControl)}
                      title="Volume control"
                    >
                      <ChevronUp className="h-4 w-4" />
                    </Button>
                  </div>
                  
                  {/* Volume Control Dropdown */}
                  {showVolumeControl && (
                    <div className="absolute bottom-full right-0 mb-2 p-3 bg-white rounded-lg shadow-xl border border-gray-200 w-48">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-700">Volume</span>
                          <span className="text-xs text-gray-500">{Math.round(volume * 100)}%</span>
                        </div>
                        
                        {/* Volume Up/Down Buttons */}
                        <div className="flex items-center justify-center space-x-4">
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8"
                            onClick={decreaseVolume}
                            disabled={volume <= 0}
                          >
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                          
                          <div className="flex-1">
                            <Slider
                              value={[volume]}
                              max={1}
                              step={0.1}
                              onValueChange={(value) => updateVolume(value[0])}
                              className="w-full"
                            />
                          </div>
                          
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8"
                            onClick={increaseVolume}
                            disabled={volume >= 1}
                          >
                            <ChevronUp className="h-4 w-4" />
                          </Button>
                        </div>
                        
                        {/* Volume Indicators */}
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <span>Low</span>
                          <div className="flex items-center space-x-2">
                            {[0, 0.25, 0.5, 0.75, 1].map((level) => (
                              <div
                                key={level}
                                className={`h-2 w-2 rounded-full ${
                                  volume >= level 
                                    ? soundEnabled ? 'bg-green-500' : 'bg-gray-400'
                                    : 'bg-gray-200'
                                }`}
                              />
                            ))}
                          </div>
                          <span>High</span>
                        </div>
                        
                        {/* Sound Status */}
                        <div className="pt-2 border-t border-gray-100">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-600">Sound</span>
                            <div className={`px-2 py-1 rounded text-xs ${
                              soundEnabled 
                                ? 'bg-green-100 text-green-700' 
                                : 'bg-gray-100 text-gray-700'
                            }`}>
                              {soundEnabled ? 'ON' : 'OFF'}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-white hover:bg-white/20"
                  onClick={resetChat}
                  disabled={connectionStatus === 'checking'}
                >
                  New Chat
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-white hover:bg-white/20"
                  onClick={() => setIsOpen(false)}
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
            </div>
          </div>

          {/* Connection Status Alert */}
          {connectionStatus !== 'connected' && (
            <Alert className={`m-4 ${
              connectionStatus === 'checking' 
                ? 'bg-yellow-50 border-yellow-200' 
                : 'bg-red-50 border-red-200'
            }`}>
              <AlertCircle className={`h-4 w-4 ${
                connectionStatus === 'checking' ? 'text-yellow-600' : 'text-red-600'
              }`} />
              <AlertDescription className={`text-sm ${
                connectionStatus === 'checking' ? 'text-yellow-700' : 'text-red-700'
              }`}>
                {connectionStatus === 'checking' 
                  ? 'Connecting to chatbot service...'
                  : 'Unable to connect to chatbot service. Please ensure the backend server is running on port 5001.'
                }
                <div className="mt-2 flex space-x-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={testConnection}
                    disabled={connectionStatus === 'checking'}
                    className={connectionStatus === 'checking' 
                      ? 'border-yellow-300 text-yellow-700' 
                      : 'border-red-300 text-red-700'
                    }
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Retry Connection
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Chat Messages */}
          <ScrollArea 
            ref={scrollAreaRef}
            className="flex-1 p-4 overflow-y-auto"
          >
            <div className="space-y-4">
              {chatHistory.map((chat) => (
                <div
                  key={chat.id}
                  className={`flex ${chat.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl p-3 ${
                      chat.type === 'user'
                        ? 'bg-green-600 text-white rounded-br-none'
                        : chat.type === 'system'
                        ? 'bg-blue-100 text-blue-800'
                        : chat.isError
                        ? 'bg-red-100 text-red-800 border border-red-200'
                        : 'bg-gray-100 text-gray-800 rounded-bl-none'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <p className="whitespace-pre-wrap flex-1">{chat.message}</p>
                      <span className="text-xs opacity-70 ml-2 whitespace-nowrap">
                        {formatTime(chat.timestamp)}
                      </span>
                    </div>
                    
                    {/* Bot metadata */}
                    {chat.type === 'bot' && !chat.isError && (
                      <div className="mt-2 pt-2 border-t border-gray-300/30">
                        {chat.intent && (
                          <div className="flex items-center justify-between text-xs mb-2">
                            <span className="text-gray-500">
                              Category: <span className="font-medium">{chat.intent}</span>
                            </span>
                            {chat.confidence !== undefined && (
                              <span className={`px-2 py-1 rounded-full text-xs ${
                                chat.confidence > 0.7 ? 'bg-green-100 text-green-800' :
                                chat.confidence > 0.4 ? 'bg-yellow-100 text-yellow-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {Math.round(chat.confidence * 100)}% confidence
                              </span>
                            )}
                          </div>
                        )}
                        
                        {/* Suggestions */}
                        {chat.suggestions && chat.suggestions.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs text-gray-500 mb-1">Related questions:</p>
                            <div className="flex flex-wrap gap-1">
                              {chat.suggestions.slice(0, 3).map((suggestion, idx) => (
                                <button
                                  key={idx}
                                  onClick={() => handleSuggestionClick(suggestion)}
                                  disabled={connectionStatus !== 'connected'}
                                  className="text-xs px-2 py-1 bg-white/50 hover:bg-white/80 disabled:opacity-50 disabled:cursor-not-allowed rounded-full text-gray-700 transition-colors"
                                >
                                  {suggestion}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Feedback buttons */}
                        {chat.log_id && (
                          <div className="mt-2 pt-2 border-t border-gray-300/30">
                            <p className="text-xs text-gray-500 mb-1">Was this helpful?</p>
                            <div className="flex space-x-2">
                              <button
                                onClick={() => handleFeedback(chat.log_id, 5)}
                                className="text-xs px-2 py-1 bg-green-100 hover:bg-green-200 text-green-700 rounded-full transition-colors flex items-center"
                              >
                                <ThumbsUp className="h-3 w-3 mr-1" /> Yes
                              </button>
                              <button
                                onClick={() => handleFeedback(chat.log_id, 1)}
                                className="text-xs px-2 py-1 bg-red-100 hover:bg-red-200 text-red-700 rounded-full transition-colors flex items-center"
                              >
                                <ThumbsDown className="h-3 w-3 mr-1" /> No
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {/* Loading indicator */}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 text-gray-800 rounded-2xl rounded-bl-none p-3">
                    <div className="flex items-center space-x-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
                      </div>
                      <span className="text-xs text-gray-600">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Input Area */}
          <div className="p-4 border-t">
            <div className="flex space-x-2">
              <Input
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={
                  connectionStatus === 'connected' 
                    ? "Type your banking question here..."
                    : "Service unavailable. Please check connection."
                }
                disabled={isLoading || connectionStatus !== 'connected'}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                disabled={isLoading || !userInput.trim() || connectionStatus !== 'connected'}
                className={`${
                  connectionStatus === 'connected' 
                    ? 'bg-green-600 hover:bg-green-700' 
                    : 'bg-gray-400 cursor-not-allowed'
                }`}
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            
            {/* Quick Suggestions */}
            {connectionStatus === 'connected' && (
              <div className="mt-2 flex flex-wrap gap-1">
                {['Account balance', 'Loan information', 'Branch locations', 'Customer support'].map((text, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSuggestionClick(text)}
                    disabled={isLoading}
                    className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded-full text-gray-700 transition-colors"
                  >
                    {text}
                  </button>
                ))}
              </div>
            )}
          </div>
          
          {/* Status Bar */}
          <div className="px-4 py-2 border-t text-xs text-gray-500 flex justify-between items-center bg-gray-50">
            <div className="flex items-center space-x-3">
              <div className="flex items-center">
                <div className={`h-2 w-2 rounded-full mr-1 ${
                  connectionStatus === 'connected' 
                    ? 'bg-green-500 animate-pulse' 
                    : connectionStatus === 'checking'
                    ? 'bg-yellow-500 animate-pulse'
                    : 'bg-red-500'
                }`} />
                <span>
                  {connectionStatus === 'connected' 
                    ? 'Connected' 
                    : connectionStatus === 'checking'
                    ? 'Connecting...'
                    : 'Disconnected'}
                </span>
              </div>
              <div className="flex items-center">
                {soundEnabled ? (
                  <Volume2 className="h-3 w-3 mr-1" />
                ) : (
                  <VolumeX className="h-3 w-3 mr-1" />
                )}
                <span>{Math.round(volume * 100)}%</span>
              </div>
            </div>
            <span className="text-gray-400" title={sessionId}>
              ID: {sessionId?.substring(0, 6)}...
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chatbot;





