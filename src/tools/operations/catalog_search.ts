import { catalogTable, catalogVectorStore, chunksVectorStore } from "../../lancedb/client.js";
import { BaseTool, ToolParams } from "../base/tool.js";
import * as path from 'path';

export interface CatalogSearchParams extends ToolParams {
  text: string;
}

export class CatalogSearchTool extends BaseTool<CatalogSearchParams> {
  name = "catalog_search";
  description = "Search for relevant documents in the catalog";
  inputSchema = {
    type: "object" as const,
    properties: {
      text: {
        type: "string",
        description: "Search string",
        default: {},
      },
    },
    required: ["text"],
  };

  async execute(params: CatalogSearchParams) {
    try {
      const retriever = catalogVectorStore.asRetriever({});
      const results = await retriever.invoke(params.text);

      // Format results with file references
      const formattedResults = this.formatResultsWithReferences(results);

      return {
        content: [
          { type: "text" as const, text: formattedResults },
        ],
        isError: false,
      };
    } catch (error) {
      return this.handleError(error);
    }
  }

  private formatResultsWithReferences(results: any[]): string {
    if (!results || results.length === 0) {
      return "No results found.";
    }

    let formattedOutput = "Search Results:\n\n";
    
    results.forEach((result, index) => {
      const fileName = result.metadata?.source ? 
        result.metadata.source.split('/').pop() : 'Unknown file';
      
      formattedOutput += `**Result ${index + 1}**\n`;
      formattedOutput += `📄 **Source**: ${fileName}\n`;
      if (result.metadata?.source) {
        formattedOutput += `🔗 **File Path**: ${result.metadata.source}\n`;
      }
      formattedOutput += `📝 **Content**: ${result.pageContent}\n`;
      formattedOutput += "---\n\n";
    });
    
    return formattedOutput;
  }
}
