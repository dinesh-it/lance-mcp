import * as fs from 'fs';
import * as path from 'path';
import sharp from 'sharp';
const pdf2pic = require('pdf2pic');
import { Ollama } from "@langchain/ollama";
import { Document } from "@langchain/core/documents";
import * as defaults from './config';

export interface ImageProcessingResult {
  description: string;
  imagePath: string;
  source: string;
  pageNumber?: number;
}

export class ImageProcessor {
  private visionModel: Ollama;

  constructor() {
    this.visionModel = new Ollama({ 
      model: defaults.VISION_MODEL,
      baseUrl: 'http://127.0.0.1:11434'
    });
  }

  /**
   * Extract images from a PDF file
   */
  async extractImagesFromPDF(pdfPath: string, tempDir: string): Promise<string[]> {
    try {
      const options = {
        density: 100,
        saveFilename: path.basename(pdfPath, '.pdf'),
        savePath: tempDir,
        format: 'png',
        width: 1024,
        height: 1024
      };

      const convertToPic = pdf2pic.fromPath(pdfPath, options);
      const results = await convertToPic.bulk(-1, { responseType: 'image' });
      
      const imagePaths: string[] = [];
      for (const result of results) {
        if (result.path) {
          imagePaths.push(result.path);
        }
      }
      
      return imagePaths;
    } catch (error) {
      console.error(`Error extracting images from PDF ${pdfPath}:`, error);
      return [];
    }
  }

  /**
   * Process standalone image file
   */
  async processStandaloneImage(imagePath: string, tempDir: string): Promise<string> {
    try {
      // Optimize image for vision model processing
      const optimizedPath = path.join(tempDir, `optimized_${path.basename(imagePath)}`);
      
      await sharp(imagePath)
        .resize(1024, 1024, { 
          fit: 'inside',
          withoutEnlargement: true 
        })
        .png()
        .toFile(optimizedPath);
      
      return optimizedPath;
    } catch (error) {
      console.error(`Error processing image ${imagePath}:`, error);
      return imagePath; // Return original if optimization fails
    }
  }

  /**
   * Generate description for an image using vision model
   */
  async generateImageDescription(imagePath: string): Promise<string> {
    try {
      // For now, create a basic description with OCR placeholder
      // This will be enhanced when proper vision models are integrated
      const fileName = path.basename(imagePath);
      const fileExt = path.extname(imagePath).toLowerCase();
      
      // Basic image metadata
      let description = `Image file: ${fileName} (${fileExt})`;
      
      try {
        // Try to get image dimensions using sharp
        const metadata = await sharp(imagePath).metadata();
        if (metadata.width && metadata.height) {
          description += ` - Dimensions: ${metadata.width}x${metadata.height}`;
        }
        if (metadata.format) {
          description += ` - Format: ${metadata.format}`;
        }
      } catch (metadataError) {
        console.warn(`Could not extract metadata from ${imagePath}:`, metadataError);
      }
      
      // Placeholder for future vision model integration
      description += " - Visual content analysis will be available when vision model is properly configured";
      
      return description;
    } catch (error) {
      console.error(`Error generating description for image ${imagePath}:`, error);
      return `Image file: ${path.basename(imagePath)} - Description could not be generated`;
    }
  }

  /**
   * Get MIME type for image file
   */
  private getMimeType(imagePath: string): string {
    const ext = path.extname(imagePath).toLowerCase();
    switch (ext) {
      case '.png': return 'image/png';
      case '.jpg':
      case '.jpeg': return 'image/jpeg';
      case '.gif': return 'image/gif';
      case '.webp': return 'image/webp';
      default: return 'image/png';
    }
  }

  /**
   * Process all images from a PDF file
   */
  async processImagesFromPDF(pdfPath: string, tempDir: string): Promise<ImageProcessingResult[]> {
    const results: ImageProcessingResult[] = [];
    
    try {
      const imagePaths = await this.extractImagesFromPDF(pdfPath, tempDir);
      
      for (let i = 0; i < imagePaths.length; i++) {
        const imagePath = imagePaths[i];
        const description = await this.generateImageDescription(imagePath);
        
        results.push({
          description,
          imagePath,
          source: pdfPath,
          pageNumber: i + 1
        });
      }
    } catch (error) {
      console.error(`Error processing images from PDF ${pdfPath}:`, error);
    }
    
    return results;
  }

  /**
   * Process a standalone image file
   */
  async processStandaloneImageFile(imagePath: string, tempDir: string): Promise<ImageProcessingResult | null> {
    try {
      const optimizedPath = await this.processStandaloneImage(imagePath, tempDir);
      const description = await this.generateImageDescription(optimizedPath);
      
      return {
        description,
        imagePath: optimizedPath,
        source: imagePath
      };
    } catch (error) {
      console.error(`Error processing standalone image ${imagePath}:`, error);
      return null;
    }
  }

  /**
   * Convert image processing results to LangChain documents
   */
  resultsToDocuments(results: ImageProcessingResult[]): Document[] {
    return results.map(result => {
      const metadata = {
        source: result.source,
        type: 'image',
        imagePath: result.imagePath,
        ...(result.pageNumber && { pageNumber: result.pageNumber })
      };

      return new Document({
        pageContent: `[IMAGE] ${result.description}`,
        metadata
      });
    });
  }

  /**
   * Check if file is a supported image format
   */
  isSupportedImageFormat(filePath: string): boolean {
    const supportedExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif'];
    const ext = path.extname(filePath).toLowerCase();
    return supportedExtensions.includes(ext);
  }

  /**
   * Clean up temporary files
   */
  async cleanupTempFiles(tempDir: string): Promise<void> {
    try {
      if (fs.existsSync(tempDir)) {
        const files = await fs.promises.readdir(tempDir);
        for (const file of files) {
          await fs.promises.unlink(path.join(tempDir, file));
        }
        await fs.promises.rmdir(tempDir);
      }
    } catch (error) {
      console.error('Error cleaning up temp files:', error);
    }
  }
}