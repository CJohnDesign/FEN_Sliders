import OBSWebSocket from 'obs-websocket-js';

interface OBSConfig {
  ip: string;
  port: number;
  password: string;
}

interface OBSConnectionStatus {
  connected: boolean;
  error?: string;
}

interface OBSConnectionResponse {
  obsWebSocketVersion: string;
  rpcVersion: number;
  negotiatedRpcVersion: number;
  authentication?: {
    challenge: string;
    salt: string;
  };
}

interface HealthCheckResult {
  isConnected: boolean;
  isRecording: boolean;
  lastError: string | null;
  reconnectAttempts: number;
  uptime: number;
  lastHealthCheck: Date;
}

class OBSService {
  private obs: OBSWebSocket;
  private config: OBSConfig;
  private static instance: OBSService;
  private isRecording: boolean = false;
  private desiredRecordingState: boolean = false; // Track what state we want OBS to be in
  private connectionPromise: Promise<OBSConnectionResponse> | null = null;
  private lastError: string | null = null;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private baseReconnectDelay: number = 1000; // Start with 1 second
  private connectionStartTime: number | null = null;
  private lastHealthCheck: Date = new Date();
  private healthCheckInterval: ReturnType<typeof setInterval> | null = null;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

  private constructor() {
    this.obs = new OBSWebSocket();
    this.config = {
      ip: 'localhost',
      port: 4455,
      password: 'A6kDm8ellkytS6LC'
    };

    this.setupEventListeners();
    this.startHealthCheck();
  }

  private setupEventListeners() {
    this.obs.on('ConnectionOpened', () => {
      console.log('[OBS Service] WebSocket connection opened');
      this.connectionStartTime = Date.now();
      this.reconnectAttempts = 0;
    });

    this.obs.on('Identified', async () => {
      console.log('[OBS Service] WebSocket identified successfully');
      // After reconnection, verify and sync recording state
      await this.syncRecordingState();
      this.reportHealth();
    });

    this.obs.on('ConnectionClosed', () => {
      console.log('[OBS Service] WebSocket connection closed', {
        wasRecording: this.isRecording,
        desiredState: this.desiredRecordingState
      });
      // Don't change recording state on disconnect
      this.connectionPromise = null;
      this.handleDisconnect('Connection closed');
    });

    this.obs.on('ConnectionError', error => {
      console.error('[OBS Service] WebSocket error:', error);
      this.lastError = error.message;
      this.connectionPromise = null;
      this.handleDisconnect(error.message);
    });

    this.obs.on('RecordStateChanged', (data: any) => {
      const oldState = this.isRecording;
      this.isRecording = data.outputActive;
      // Update our desired state to match reality if it changes externally
      if (this.isRecording !== this.desiredRecordingState) {
        this.desiredRecordingState = this.isRecording;
      }
      console.log('[OBS Service] Recording state changed:', { 
        from: oldState, 
        to: this.isRecording, 
        outputActive: data.outputActive,
        outputPath: data.outputPath,
        desiredState: this.desiredRecordingState
      });
      this.reportHealth();
    });
  }

  private async syncRecordingState() {
    try {
      const recordingStatus = await this.obs.call('GetRecordStatus');
      const actualState = recordingStatus?.outputActive || false;
      
      console.log('[OBS Service] Syncing recording state:', {
        currentState: this.isRecording,
        actualState,
        desiredState: this.desiredRecordingState
      });

      // Update our tracking to match reality
      this.isRecording = actualState;

      // If our desired state doesn't match reality and we're connected, try to fix it
      if (this.desiredRecordingState !== actualState && this.obs.identified) {
        console.log('[OBS Service] Recording state mismatch, attempting to sync with desired state');
        try {
          if (this.desiredRecordingState) {
            await this.obs.call('StartRecord');
          } else {
            await this.obs.call('StopRecord');
          }
          // Wait briefly for OBS to update
          await new Promise(resolve => setTimeout(resolve, 500));
          // Verify the change
          const newStatus = await this.obs.call('GetRecordStatus');
          this.isRecording = newStatus?.outputActive || false;
          
          if (this.isRecording !== this.desiredRecordingState) {
            console.error('[OBS Service] Failed to sync recording state with desired state');
            // Reset desired state to match reality
            this.desiredRecordingState = this.isRecording;
          }
        } catch (error) {
          console.error('[OBS Service] Error during sync operation:', error);
          // Reset desired state to match reality on error
          this.desiredRecordingState = actualState;
        }
      }
    } catch (error) {
      console.error('[OBS Service] Error syncing recording state:', error);
    }
  }

  private async handleDisconnect(reason: string) {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[OBS Service] Max reconnection attempts reached:', {
        attempts: this.reconnectAttempts,
        lastError: reason
      });
      return;
    }

    // Calculate exponential backoff delay
    const delay = this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts);
    console.log('[OBS Service] Scheduling reconnect:', {
      attempt: this.reconnectAttempts + 1,
      delayMs: delay,
      reason
    });

    this.reconnectTimeout = setTimeout(async () => {
      this.reconnectAttempts++;
      try {
        console.log('[OBS Service] Attempting reconnect:', {
          attempt: this.reconnectAttempts,
          maxAttempts: this.maxReconnectAttempts
        });
        await this.connect();
      } catch (error) {
        console.error('[OBS Service] Reconnection failed:', error);
      }
    }, delay);
  }

  private startHealthCheck() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    // Run health check every 5 seconds
    this.healthCheckInterval = setInterval(() => {
      this.checkHealth();
    }, 20000);
  }

  private async checkHealth() {
    const health = await this.getHealthStatus();
    this.lastHealthCheck = new Date();
    this.reportHealth(health);
  }

  private reportHealth(health?: HealthCheckResult) {
    if (!health) {
      health = {
        isConnected: this.obs.identified || false,
        isRecording: this.isRecording,
        lastError: this.lastError,
        reconnectAttempts: this.reconnectAttempts,
        uptime: this.connectionStartTime ? Date.now() - this.connectionStartTime : 0,
        lastHealthCheck: this.lastHealthCheck
      };
    }

    console.log('[OBS Service] Health Report:', {
      timestamp: new Date().toISOString(),
      status: health.isConnected ? 'CONNECTED' : 'DISCONNECTED',
      recording: health.isRecording ? 'ACTIVE' : 'INACTIVE',
      desiredRecording: this.desiredRecordingState ? 'ACTIVE' : 'INACTIVE',
      uptimeSeconds: Math.floor(health.uptime / 1000),
      reconnectAttempts: health.reconnectAttempts,
      lastError: health.lastError || 'none',
      lastCheck: health.lastHealthCheck.toISOString()
    });
  }

  public async getHealthStatus(): Promise<HealthCheckResult> {
    try {
      if (this.obs.identified) {
        await this.syncRecordingState();
      }
    } catch (error) {
      console.error('[OBS Service] Health check error:', error);
    }

    return {
      isConnected: this.obs.identified || false,
      isRecording: this.isRecording,
      lastError: this.lastError,
      reconnectAttempts: this.reconnectAttempts,
      uptime: this.connectionStartTime ? Date.now() - this.connectionStartTime : 0,
      lastHealthCheck: this.lastHealthCheck
    };
  }

  public static getInstance(): OBSService {
    if (!OBSService.instance) {
      OBSService.instance = new OBSService();
    }
    return OBSService.instance;
  }

  public async connect(): Promise<OBSConnectionStatus> {
    try {
      console.log('[OBS Service] Attempting connection...', {
        currentlyIdentified: this.obs.identified,
        hasConnectionPromise: !!this.connectionPromise,
        reconnectAttempt: this.reconnectAttempts
      });

      if (this.obs.identified) {
        await this.syncRecordingState();
        return { connected: true };
      }

      if (this.connectionPromise) {
        await this.connectionPromise;
        await this.syncRecordingState();
        return { connected: true };
      }

      this.connectionPromise = this.obs.connect(`ws://${this.config.ip}:${this.config.port}`, this.config.password);
      await this.connectionPromise;
      await this.syncRecordingState();
      return { connected: true };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      console.error('[OBS Service] Connection failed:', errorMessage);
      this.lastError = errorMessage;
      this.connectionPromise = null;
      return {
        connected: false,
        error: errorMessage
      };
    }
  }

  public async disconnect(): Promise<void> {
    try {
      if (this.healthCheckInterval) {
        clearInterval(this.healthCheckInterval);
        this.healthCheckInterval = null;
      }
      if (this.reconnectTimeout) {
        clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = null;
      }

      console.log('[OBS Service] Disconnecting...', {
        wasIdentified: this.obs.identified,
        wasRecording: this.isRecording,
        uptime: this.connectionStartTime ? Date.now() - this.connectionStartTime : 0
      });
      
      this.connectionPromise = null;
      this.connectionStartTime = null;
      if (this.obs.identified) {
        await this.obs.disconnect();
      }
    } catch (error) {
      console.error('[OBS Service] Error during disconnect:', error);
      this.lastError = error instanceof Error ? error.message : 'Unknown error during disconnect';
    }
  }

  public async toggleRecording(): Promise<boolean> {
    try {
      console.log('[OBS Service] Toggle recording requested', {
        currentlyIdentified: this.obs.identified,
        currentRecordingState: this.isRecording,
        desiredState: !this.desiredRecordingState
      });

      // Update our desired state first
      this.desiredRecordingState = !this.desiredRecordingState;

      if (!this.obs.identified) {
        const status = await this.connect();
        if (!status.connected) {
          console.log('[OBS Service] Not connected, but tracking desired state:', this.desiredRecordingState);
          return this.desiredRecordingState;
        }
      }

      const recordingStatus = await this.obs.call('GetRecordStatus');
      const isCurrentlyRecording = recordingStatus?.outputActive || false;
      
      console.log('[OBS Service] Current recording status:', {
        serviceState: this.isRecording,
        obsState: isCurrentlyRecording,
        desiredState: this.desiredRecordingState
      });

      if (this.desiredRecordingState !== isCurrentlyRecording) {
        try {
          if (this.desiredRecordingState) {
            await this.obs.call('StartRecord');
            // Wait briefly for OBS to start recording
            await new Promise(resolve => setTimeout(resolve, 500));
            const newStatus = await this.obs.call('GetRecordStatus');
            if (!newStatus?.outputActive) {
              console.error('[OBS Service] Failed to start recording after attempt');
              return false;
            }
          } else {
            await this.obs.call('StopRecord');
            // Wait briefly for OBS to stop recording
            await new Promise(resolve => setTimeout(resolve, 500));
            const newStatus = await this.obs.call('GetRecordStatus');
            if (newStatus?.outputActive) {
              console.error('[OBS Service] Failed to stop recording after attempt');
              return true;
            }
          }
        } catch (error) {
          console.error('[OBS Service] Error during recording operation:', error);
          // Reset desired state on error
          this.desiredRecordingState = isCurrentlyRecording;
          return isCurrentlyRecording;
        }
      }
      
      // Get final state
      const finalStatus = await this.obs.call('GetRecordStatus');
      this.isRecording = finalStatus?.outputActive || false;
      
      console.log('[OBS Service] Final recording state:', {
        isRecording: this.isRecording,
        desiredState: this.desiredRecordingState
      });
      
      return this.isRecording;
    } catch (error) {
      console.error('[OBS Service] Error toggling recording:', error);
      this.lastError = error instanceof Error ? error.message : 'Unknown error toggling recording';
      return this.isRecording; // Return actual state instead of desired state on error
    }
  }

  public getRecordingStatus(): boolean {
    // Return our desired state if disconnected, actual state if connected
    return this.obs.identified ? this.isRecording : this.desiredRecordingState;
  }

  public isConnected(): boolean {
    return this.obs.identified || false;
  }

  public getLastError(): string | null {
    return this.lastError;
  }
}

export const obsService = OBSService.getInstance(); 