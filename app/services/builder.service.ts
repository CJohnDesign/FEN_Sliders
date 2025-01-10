import { spawn } from 'child_process';
import { z } from 'zod';

// Types
export const BuilderInput = z.object({
  deckId: z.string(),
  title: z.string(),
  template: z.string(),
  themeConfig: z.record(z.any()).optional()
});

export type BuilderInputType = z.infer<typeof BuilderInput>;

interface BuilderResult {
  status: 'success' | 'error';
  deck_id: string;
  error?: {
    error: string;
    stage: string;
  };
  slides_count?: number;
  audio_config?: {
    config_path: string;
    script_path: string;
    slide_count: number;
  };
}

export class BuilderService {
  static async createDeck(input: BuilderInputType): Promise<BuilderResult> {
    return new Promise((resolve, reject) => {
      const pythonProcess = spawn('python', [
        '-m', 'agents.builder.run',
        '--deck-id', input.deckId,
        '--title', input.title,
        '--template', input.template,
        ...(input.themeConfig ? ['--theme-config', JSON.stringify(input.themeConfig)] : [])
      ]);

      let outputData = '';
      let errorData = '';

      pythonProcess.stdout.on('data', (data) => {
        outputData += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        errorData += data.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Builder process failed: ${errorData}`));
          return;
        }

        try {
          const result = JSON.parse(outputData);
          resolve(result);
        } catch (error) {
          reject(new Error('Failed to parse builder output'));
        }
      });

      // Handle process errors
      pythonProcess.on('error', (error) => {
        reject(new Error(`Failed to start builder process: ${error.message}`));
      });

      // Set timeout
      const timeout = setTimeout(() => {
        pythonProcess.kill();
        reject(new Error('Builder process timed out'));
      }, 5 * 60 * 1000); // 5 minutes timeout

      // Clear timeout on process end
      pythonProcess.on('close', () => {
        clearTimeout(timeout);
      });
    });
  }
} 