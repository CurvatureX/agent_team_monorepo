import { POST, GET } from "./route";
import { NextRequest } from "next/server";

// Mock Next.js server components
jest.mock("next/server", () => ({
  NextRequest: jest.fn(),
  NextResponse: {
    json: jest.fn((data, init) => ({
      json: () => Promise.resolve(data),
      status: init?.status || 200,
      headers: new Map(Object.entries(init?.headers || {})),
    })),
  },
}));

// Mock OpenAI
jest.mock("openai", () => {
  return jest.fn().mockImplementation(() => ({
    embeddings: {
      create: jest.fn().mockResolvedValue({
        data: [{ embedding: new Array(1536).fill(0.1) }],
      }),
    },
  }));
});

// Mock Supabase
jest.mock("@/lib/supabase", () => ({
  supabase: {
    rpc: jest.fn(),
    from: jest.fn(() => ({
      select: jest.fn(() => ({
        select: jest.fn().mockReturnThis(),
      })),
    })),
  },
}));

describe("/api/query", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("POST", () => {
    it("should validate required query parameter", async () => {
      const mockRequest = {
        json: jest.fn().mockResolvedValue({}),
      } as any;

      const response = await POST(mockRequest);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.error).toContain("Query is required");
    });

    it("should validate query length limits", async () => {
      const longQuery = "a".repeat(1001);
      const mockRequest = {
        json: jest.fn().mockResolvedValue({ query: longQuery }),
      } as any;

      const response = await POST(mockRequest);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.error).toContain("too long");
    });

    it("should validate empty query", async () => {
      const mockRequest = {
        json: jest.fn().mockResolvedValue({ query: "   " }),
      } as any;

      const response = await POST(mockRequest);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.error).toContain("cannot be empty");
    });

    it("should validate limit parameter", async () => {
      const mockRequest = {
        json: jest.fn().mockResolvedValue({ query: "test query", limit: 100 }),
      } as any;

      const response = await POST(mockRequest);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.error).toContain("Limit must be a number between 1 and 50");
    });

    it("should validate threshold parameter", async () => {
      const mockRequest = {
        json: jest
          .fn()
          .mockResolvedValue({ query: "test query", threshold: 1.5 }),
      } as any;

      const response = await POST(mockRequest);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.error).toContain(
        "Threshold must be a number between 0 and 1"
      );
    });

    it("should handle invalid JSON", async () => {
      const mockRequest = {
        json: jest.fn().mockRejectedValue(new Error("Invalid JSON")),
      } as any;

      const response = await POST(mockRequest);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.error).toContain("Invalid JSON");
    });
  });

  describe("GET", () => {
    it("should return API status", async () => {
      const { supabase } = require("@/lib/supabase");
      supabase.from.mockReturnValue({
        select: jest.fn().mockResolvedValue({ count: 5, error: null }),
      });

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.available).toBe(true);
      expect(data.totalNodes).toBe(5);
    });
  });
});
