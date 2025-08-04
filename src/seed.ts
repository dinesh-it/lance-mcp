import * as lancedb from "@lancedb/lancedb";
import minimist from 'minimist';
import {
  RecursiveCharacterTextSplitter
} from 'langchain/text_splitter';
import {
  DirectoryLoader
} from 'langchain/document_loaders/fs/directory';
import {
  LanceDB, LanceDBArgs
} from "@langchain/community/vectorstores/lancedb";
import { Document } from "@langchain/core/documents";
import { Ollama, OllamaEmbeddings } from "@langchain/ollama";
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
import { loadSummarizationChain } from "langchain/chains";
import { BaseLanguageModelInterface, BaseLanguageModelCallOptions } from "@langchain/core/language_models/base";
import { PromptTemplate } from "@langchain/core/prompts";
import * as crypto from 'crypto';
import * as defaults from './config';
import { ImageProcessor, ImageProcessingResult } from './image-processor';

const argv: minimist.ParsedArgs = minimist(process.argv.slice(2),{boolean: "overwrite"});

const databaseDir = argv["dbpath"];
const filesDir = argv["filesdir"];
const overwrite = argv["overwrite"];

function validateArgs() {
    if (!databaseDir || !filesDir) {
        console.error("Please provide a database path (--dbpath) and a directory with files (--filesdir) to process");
        process.exit(1);
    }
    
    console.log("DATABASE PATH: ", databaseDir);
    console.log("FILES DIRECTORY: ", filesDir);
    console.log("OVERWRITE FLAG: ", overwrite);
}

const contentOverviewPromptTemplate = `Write a high-level one sentence content overview based on the text below:


"{text}"


WRITE THE CONTENT OVERVIEW ONLY, DO NOT WRITE ANYTHING ELSE:`;


const contentOverviewPrompt = new PromptTemplate({
  template: contentOverviewPromptTemplate,
  inputVariables: ["text"],
});

async function generateContentOverview(rawDocs: any, model: BaseLanguageModelInterface<any, BaseLanguageModelCallOptions>) {
  // This convenience function creates a document chain prompted to summarize a set of documents.
  const chain = loadSummarizationChain(model, { type: "map_reduce", combinePrompt: contentOverviewPrompt});
  const res = await chain.invoke({
    input_documents: rawDocs,
  });

  return res;
}

async function catalogRecordExists(catalogTable: lancedb.Table, hash: string): Promise<boolean> {
  const query = catalogTable.query().where(`hash="${hash}"`).limit(1);
  const results = await query.toArray();
  return results.length > 0;
}

const directoryLoader = new DirectoryLoader(
  filesDir,
  {
   ".pdf": (path: string) => new PDFLoader(path),
  },
);

const imageProcessor = new ImageProcessor();

const model = new Ollama({ 
  model: defaults.SUMMARIZATION_MODEL,
  baseUrl: 'http://127.0.0.1:11434'
});

// prepares documents for summarization
// returns already existing sources and new catalog records
async function processDocuments(rawDocs: any, catalogTable: lancedb.Table, skipExistsCheck: boolean) {
    // group rawDocs by source for further processing
    const docsBySource = rawDocs.reduce((acc: Record<string, any[]>, doc: any) => {
        const source = doc.metadata.source;
        if (!acc[source]) {
            acc[source] = [];
        }
        acc[source].push(doc);
        return acc;
    }, {});

    let skipSources = [];
    let catalogRecords = [];

    // iterate over individual sources and get their summaries
    for (const [source, docs] of Object.entries(docsBySource)) {
        // Calculate hash of the source document
        const fileContent = await fs.promises.readFile(source);
        const hash = crypto.createHash('sha256').update(fileContent).digest('hex');

        // Check if a source document with the same hash already exists in the catalog
        const exists = skipExistsCheck ? false : await catalogRecordExists(catalogTable, hash);
        if (exists) {
            console.log(`Document with hash ${hash} already exists in the catalog. Skipping...`);
            skipSources.push(source);
        } else {
            const contentOverview = await generateContentOverview(docs, model);
            console.log(`Content overview for source ${source}:`, contentOverview);
            catalogRecords.push(new Document({ pageContent: contentOverview["text"], metadata: { source, hash } }));
        }
    }

    return { skipSources, catalogRecords };
}

// Find all image files in the directory
async function findImageFiles(dir: string): Promise<string[]> {
    const imageFiles: string[] = [];
    
    async function scanDirectory(currentDir: string) {
        const entries = await fs.promises.readdir(currentDir, { withFileTypes: true });
        
        for (const entry of entries) {
            const fullPath = path.join(currentDir, entry.name);
            
            if (entry.isDirectory()) {
                await scanDirectory(fullPath);
            } else if (entry.isFile() && imageProcessor.isSupportedImageFormat(fullPath)) {
                imageFiles.push(fullPath);
            }
        }
    }
    
    await scanDirectory(dir);
    return imageFiles;
}

// Process images from PDFs and standalone image files
async function processImages(rawDocs: Document[], skipSources: string[]): Promise<Document[]> {
    const imageDocuments: Document[] = [];
    const tempDir = path.join(os.tmpdir(), 'lance-mcp-images');
    
    try {
        // Create temp directory
        if (!fs.existsSync(tempDir)) {
            await fs.promises.mkdir(tempDir, { recursive: true });
        }
        
        console.log("Processing images from PDFs...");
        // Process images from PDFs
        const pdfSources = new Set();
        for (const doc of rawDocs) {
            if (!skipSources.includes(doc.metadata.source) && 
                doc.metadata.source.toLowerCase().endsWith('.pdf')) {
                pdfSources.add(doc.metadata.source);
            }
        }
        
        for (const pdfPath of pdfSources) {
            console.log(`Extracting images from PDF: ${pdfPath}`);
            const imageResults = await imageProcessor.processImagesFromPDF(pdfPath as string, tempDir);
            const imageDocs = imageProcessor.resultsToDocuments(imageResults);
            imageDocuments.push(...imageDocs);
        }
        
        console.log("Processing standalone image files...");
        // Process standalone image files
        const imageFiles = await findImageFiles(filesDir);
        for (const imagePath of imageFiles) {
            console.log(`Processing image: ${imagePath}`);
            const result = await imageProcessor.processStandaloneImageFile(imagePath, tempDir);
            if (result) {
                const imageDocs = imageProcessor.resultsToDocuments([result]);
                imageDocuments.push(...imageDocs);
            }
        }
        
        console.log(`Processed ${imageDocuments.length} images total`);
        
    } catch (error) {
        console.error('Error processing images:', error);
    } finally {
        // Clean up temp directory
        await imageProcessor.cleanupTempFiles(tempDir);
    }
    
    return imageDocuments;
}

async function seed() {
    validateArgs();

    const db = await lancedb.connect(databaseDir);

    let catalogTable : lancedb.Table;
    let catalogTableExists = true;
    let chunksTable : lancedb.Table;

    try {
        catalogTable = await db.openTable(defaults.CATALOG_TABLE_NAME);
    } catch (e) {
        console.error(`Looks like the catalog table "${defaults.CATALOG_TABLE_NAME}" doesn't exist. We'll create it later.`);
        catalogTableExists = false;
    }

    try {
        chunksTable = await db.openTable(defaults.CHUNKS_TABLE_NAME);
    } catch (e) {
        console.error(`Looks like the chunks table "${defaults.CHUNKS_TABLE_NAME}" doesn't exist. We'll create it later.`);
    }

    // try dropping the tables if we need to overwrite
    if (overwrite) {
        try {
            await db.dropTable(defaults.CATALOG_TABLE_NAME);
            await db.dropTable(defaults.CHUNKS_TABLE_NAME);
        } catch (e) {
            console.log("Error dropping tables. Maybe they don't exist!");
        }
    }

    // load files from the files path
    console.log("Loading files...")
    const rawDocs = await directoryLoader.load();

    // overwrite the metadata as large metadata can give lancedb problems
    for (const doc of rawDocs) {
        doc.metadata = { loc: doc.metadata.loc, source: doc.metadata.source };
    }

    console.log("Loading LanceDB catalog store...")

    const { skipSources, catalogRecords } = await processDocuments(rawDocs, catalogTable, overwrite || !catalogTableExists);
    const catalogStore = catalogRecords.length > 0 ? 
        await LanceDB.fromDocuments(catalogRecords, 
            new OllamaEmbeddings({
          model: defaults.EMBEDDING_MODEL,
          baseUrl: 'http://127.0.0.1:11434'
        }), 
            { mode: overwrite ? "overwrite" : undefined, uri: databaseDir, tableName: defaults.CATALOG_TABLE_NAME } as LanceDBArgs) :
        new LanceDB(new OllamaEmbeddings({
          model: defaults.EMBEDDING_MODEL,
          baseUrl: 'http://127.0.0.1:11434'
        }), { uri: databaseDir, table: catalogTable});
    console.log(catalogStore);

    console.log("Number of new catalog records: ", catalogRecords.length);
    console.log("Number of skipped sources: ", skipSources.length);
    //remove skipped sources from rawDocs
    const filteredRawDocs = rawDocs.filter((doc: any) => !skipSources.includes(doc.metadata.source));

    // Process images from PDFs and standalone image files
    console.log("Processing images...");
    const imageDocuments = await processImages(rawDocs, skipSources);

    console.log("Loading LanceDB vector store...")
    const splitter = new RecursiveCharacterTextSplitter({
        chunkSize: 500,
        chunkOverlap: 10,
      });
    
    // Split text documents
    const textDocs = await splitter.splitDocuments(filteredRawDocs);
    
    // Combine text documents with image documents
    const allDocs = [...textDocs, ...imageDocuments];
    
    const vectorStore = allDocs.length > 0 ? 
        await LanceDB.fromDocuments(allDocs, 
        new OllamaEmbeddings({
          model: defaults.EMBEDDING_MODEL,
          baseUrl: 'http://127.0.0.1:11434'
        }), 
        { mode: overwrite ? "overwrite" : undefined, uri: databaseDir, tableName: defaults.CHUNKS_TABLE_NAME } as LanceDBArgs) :
        new LanceDB(new OllamaEmbeddings({
          model: defaults.EMBEDDING_MODEL,
          baseUrl: 'http://127.0.0.1:11434'
        }), { uri: databaseDir, table: chunksTable });

    console.log("Number of new text chunks: ", textDocs.length);
    console.log("Number of new image chunks: ", imageDocuments.length);
    console.log("Total chunks: ", allDocs.length);
    console.log(vectorStore);
}

seed();
