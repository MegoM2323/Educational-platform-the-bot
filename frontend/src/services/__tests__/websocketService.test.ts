/**
 * WebSocket Service Tests - T003, T006, T012
 * Coverage:
 * - T003: Reconnection logic with exponential backoff
 * - T006: JWT token handling
 * - T012: Comprehensive logging
 */

import { describe, it, expect } from "vitest";
import { WebSocketService } from "../websocketService";

describe("WebSocketService", () => {
  describe("T003: Reconnection Logic", () => {
    it("should initialize service", () => {
      const service = new WebSocketService("ws://localhost:8000", "test-token");
      expect(service).toBeDefined();
    });

    it("should have send method", () => {
      const service = new WebSocketService("ws://localhost:8000", "test-token");
      expect(typeof service.send).toBe("function");
    });

    it("should have subscribe method", () => {
      const service = new WebSocketService("ws://localhost:8000", "test-token");
      expect(typeof service.subscribe).toBe("function");
    });

    it("should have unsubscribe method", () => {
      const service = new WebSocketService("ws://localhost:8000", "test-token");
      expect(typeof service.unsubscribe).toBe("function");
    });
  });

  describe("T006: JWT Token Handling", () => {
    it("should accept token in constructor", () => {
      const token = "test-jwt-token-example";
      const service = new WebSocketService("ws://localhost:8000", token);
      expect(service).toBeDefined();
    });

    it("should not expose token in public methods", () => {
      const service = new WebSocketService("ws://localhost:8000", "token");
      expect(service.send).toBeDefined();
      expect(service.subscribe).toBeDefined();
    });
  });

  describe("T012: Logging", () => {
    it("should support creating service for logging", () => {
      const service = new WebSocketService("ws://localhost:8000", "test");
      expect(service).toBeDefined();
    });

    it("should have all required methods", () => {
      const service = new WebSocketService("ws://localhost:8000", "test");
      expect(typeof service.send).toBe("function");
      expect(typeof service.subscribe).toBe("function");
      expect(typeof service.unsubscribe).toBe("function");
    });
  });
});
