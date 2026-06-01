import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WikiConversationGovernanceSettingsPage } from "@/features/wiki/WikiConversationGovernanceSettingsPage";

const mocks = vi.hoisted(() => ({
  clearWikiConversationMetricsBackfillJobHistory: vi.fn(),
  enqueueWikiConversationMetricsBackfill: vi.fn(),
  getLatestWikiConversationMetricsBackfillJob: vi.fn(),
  getWikiConversationMetricsBackfillJobChainDetail: vi.fn(),
  getWikiConversationMetricsBackfillJobChainSummary: vi.fn(),
  getStoredAccessToken: vi.fn(),
  getWikiConversationGovernanceConfig: vi.fn(),
  listWikiConversationMetricsBackfillJobChains: vi.fn(),
  retryWikiConversationMetricsBackfillJob: vi.fn(),
  updateWikiConversationGovernanceConfig: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  clearWikiConversationMetricsBackfillJobHistory: mocks.clearWikiConversationMetricsBackfillJobHistory,
  enqueueWikiConversationMetricsBackfill: mocks.enqueueWikiConversationMetricsBackfill,
  getLatestWikiConversationMetricsBackfillJob: mocks.getLatestWikiConversationMetricsBackfillJob,
  getWikiConversationMetricsBackfillJobChainDetail: mocks.getWikiConversationMetricsBackfillJobChainDetail,
  getWikiConversationMetricsBackfillJobChainSummary: mocks.getWikiConversationMetricsBackfillJobChainSummary,
  getWikiConversationGovernanceConfig: mocks.getWikiConversationGovernanceConfig,
  listWikiConversationMetricsBackfillJobChains: mocks.listWikiConversationMetricsBackfillJobChains,
  retryWikiConversationMetricsBackfillJob: mocks.retryWikiConversationMetricsBackfillJob,
  updateWikiConversationGovernanceConfig: mocks.updateWikiConversationGovernanceConfig,
}));

describe("WikiConversationGovernanceSettingsPage", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getWikiConversationGovernanceConfig.mockResolvedValue({
      fallback_heavy_threshold: 2,
      no_match_repeated_threshold: 2,
      high_latency_ms_threshold: 1000,
      data_complete_from: "2026-05-01",
      last_backfill_at: "2026-05-29T07:00:00Z",
      updated_by: "admin",
      updated_at: "2026-05-29T07:00:00Z",
    });
    mocks.getLatestWikiConversationMetricsBackfillJob.mockResolvedValue({
      id: "job-1",
      parent_job_id: null,
      retry_count: 0,
      status: "completed",
      requested_by: "admin",
      start_date: "2026-05-01",
      end_date: "2026-05-03",
      data_complete_from: "2026-05-01",
      progress_total_days: 3,
      progress_completed_days: 3,
      progress_percent: 100,
      progress_message: "Backfill completato.",
      error_detail: null,
      created_at: "2026-05-29T07:00:00Z",
      started_at: "2026-05-29T07:01:00Z",
      finished_at: "2026-05-29T07:10:00Z",
    });
    mocks.getWikiConversationMetricsBackfillJobChainSummary.mockResolvedValue({
      total_chains: 1,
      failed_chains: 1,
      chains_with_active_retry: 0,
      completed_chains: 0,
      avg_retries_per_chain: 0,
      oldest_active_chain_created_at: null,
    });
    mocks.listWikiConversationMetricsBackfillJobChains
      .mockResolvedValueOnce({
        items: [
          {
            root_job_id: "job-1",
            chain_status: "failed",
            retry_count_total: 0,
            has_active_retry: false,
            oldest_created_at: "2026-05-29T07:00:00Z",
            latest_job: {
              id: "job-1",
              parent_job_id: null,
              retry_count: 0,
              status: "failed",
              requested_by: "admin",
              start_date: "2026-05-01",
              end_date: "2026-05-03",
              data_complete_from: "2026-05-01",
              progress_total_days: 3,
              progress_completed_days: 1,
              progress_percent: 33,
              progress_message: "Backfill fallito.",
              error_detail: "boom",
              created_at: "2026-05-29T07:00:00Z",
              started_at: "2026-05-29T07:01:00Z",
              finished_at: "2026-05-29T07:10:00Z",
              queue_position: null,
              is_latest_attempt: true,
            },
            items: [
              {
                id: "job-1",
                parent_job_id: null,
                retry_count: 0,
                status: "failed",
                requested_by: "admin",
                start_date: "2026-05-01",
                end_date: "2026-05-03",
                data_complete_from: "2026-05-01",
                progress_total_days: 3,
                progress_completed_days: 1,
                progress_percent: 33,
                progress_message: "Backfill fallito.",
                error_detail: "boom",
                created_at: "2026-05-29T07:00:00Z",
                started_at: "2026-05-29T07:01:00Z",
                finished_at: "2026-05-29T07:10:00Z",
                queue_position: null,
                is_latest_attempt: true,
              },
            ],
          },
        ],
      })
      .mockResolvedValue({
        items: [
          {
            root_job_id: "job-1",
            chain_status: "pending",
            retry_count_total: 1,
            has_active_retry: true,
            oldest_created_at: "2026-05-29T07:00:00Z",
            latest_job: {
              id: "job-3",
              parent_job_id: "job-1",
              retry_count: 1,
              status: "pending",
              requested_by: "admin",
              start_date: "2026-05-01",
              end_date: "2026-05-03",
              data_complete_from: "2026-05-01",
              progress_total_days: 3,
              progress_completed_days: 0,
              progress_percent: 0,
              progress_message: "Backfill accodato.",
              error_detail: null,
              created_at: "2026-05-29T07:11:00Z",
              started_at: null,
              finished_at: null,
              queue_position: 1,
              is_latest_attempt: true,
            },
            items: [
              {
                id: "job-1",
                parent_job_id: null,
                retry_count: 0,
                status: "failed",
                requested_by: "admin",
                start_date: "2026-05-01",
                end_date: "2026-05-03",
                data_complete_from: "2026-05-01",
                progress_total_days: 3,
                progress_completed_days: 1,
                progress_percent: 33,
                progress_message: "Backfill fallito.",
                error_detail: "boom",
                created_at: "2026-05-29T07:00:00Z",
                started_at: "2026-05-29T07:01:00Z",
                finished_at: "2026-05-29T07:10:00Z",
                queue_position: null,
                is_latest_attempt: false,
              },
              {
                id: "job-3",
                parent_job_id: "job-1",
                retry_count: 1,
                status: "pending",
                requested_by: "admin",
                start_date: "2026-05-01",
                end_date: "2026-05-03",
                data_complete_from: "2026-05-01",
                progress_total_days: 3,
                progress_completed_days: 0,
                progress_percent: 0,
                progress_message: "Backfill accodato.",
                error_detail: null,
                created_at: "2026-05-29T07:11:00Z",
                started_at: null,
                finished_at: null,
                queue_position: 1,
                is_latest_attempt: true,
              },
            ],
          },
        ],
      });
    mocks.getWikiConversationMetricsBackfillJobChainDetail
      .mockResolvedValueOnce({
        root_job_id: "job-1",
        chain_status: "failed",
        retry_count_total: 0,
        has_active_retry: false,
        oldest_created_at: "2026-05-29T07:00:00Z",
        latest_job: {
          id: "job-1",
          parent_job_id: null,
          retry_count: 0,
          status: "failed",
          requested_by: "admin",
          start_date: "2026-05-01",
          end_date: "2026-05-03",
          data_complete_from: "2026-05-01",
          progress_total_days: 3,
          progress_completed_days: 1,
          progress_percent: 33,
          progress_message: "Backfill fallito.",
          error_detail: "boom",
          created_at: "2026-05-29T07:00:00Z",
          started_at: "2026-05-29T07:01:00Z",
          finished_at: "2026-05-29T07:10:00Z",
          queue_position: null,
          is_latest_attempt: true,
        },
        items: [
          {
            id: "job-1",
            parent_job_id: null,
            retry_count: 0,
            status: "failed",
            requested_by: "admin",
            start_date: "2026-05-01",
            end_date: "2026-05-03",
            data_complete_from: "2026-05-01",
            progress_total_days: 3,
            progress_completed_days: 1,
            progress_percent: 33,
            progress_message: "Backfill fallito.",
            error_detail: "boom",
            created_at: "2026-05-29T07:00:00Z",
            started_at: "2026-05-29T07:01:00Z",
            finished_at: "2026-05-29T07:10:00Z",
            queue_position: null,
            is_latest_attempt: true,
          },
        ],
      })
      .mockResolvedValue({
        root_job_id: "job-1",
        chain_status: "pending",
        retry_count_total: 1,
        has_active_retry: true,
        oldest_created_at: "2026-05-29T07:00:00Z",
        latest_job: {
          id: "job-3",
          parent_job_id: "job-1",
          retry_count: 1,
          status: "pending",
          requested_by: "admin",
          start_date: "2026-05-01",
          end_date: "2026-05-03",
          data_complete_from: "2026-05-01",
          progress_total_days: 3,
          progress_completed_days: 0,
          progress_percent: 0,
          progress_message: "Backfill accodato.",
          error_detail: null,
          created_at: "2026-05-29T07:11:00Z",
          started_at: null,
          finished_at: null,
          queue_position: 1,
          is_latest_attempt: true,
        },
        items: [
          {
            id: "job-1",
            parent_job_id: null,
            retry_count: 0,
            status: "failed",
            requested_by: "admin",
            start_date: "2026-05-01",
            end_date: "2026-05-03",
            data_complete_from: "2026-05-01",
            progress_total_days: 3,
            progress_completed_days: 1,
            progress_percent: 33,
            progress_message: "Backfill fallito.",
            error_detail: "boom",
            created_at: "2026-05-29T07:00:00Z",
            started_at: "2026-05-29T07:01:00Z",
            finished_at: "2026-05-29T07:10:00Z",
            queue_position: null,
            is_latest_attempt: false,
          },
          {
            id: "job-3",
            parent_job_id: "job-1",
            retry_count: 1,
            status: "pending",
            requested_by: "admin",
            start_date: "2026-05-01",
            end_date: "2026-05-03",
            data_complete_from: "2026-05-01",
            progress_total_days: 3,
            progress_completed_days: 0,
            progress_percent: 0,
            progress_message: "Backfill accodato.",
            error_detail: null,
            created_at: "2026-05-29T07:11:00Z",
            started_at: null,
            finished_at: null,
            queue_position: 1,
            is_latest_attempt: true,
          },
        ],
      });
    mocks.updateWikiConversationGovernanceConfig.mockResolvedValue({
      fallback_heavy_threshold: 3,
      no_match_repeated_threshold: 2,
      high_latency_ms_threshold: 1000,
      data_complete_from: "2026-05-01",
      last_backfill_at: "2026-05-29T07:00:00Z",
      updated_by: "admin",
      updated_at: "2026-05-29T07:05:00Z",
    });
    mocks.enqueueWikiConversationMetricsBackfill.mockResolvedValue({
      id: "job-2",
      parent_job_id: null,
      retry_count: 0,
      status: "pending",
      requested_by: "admin",
      start_date: "2026-05-29",
      end_date: "2026-05-29",
      data_complete_from: "2026-05-01",
      progress_total_days: 1,
      progress_completed_days: 0,
      progress_percent: 0,
      progress_message: "Backfill accodato.",
      error_detail: null,
      created_at: "2026-05-29T07:10:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.retryWikiConversationMetricsBackfillJob.mockResolvedValue({
      id: "job-3",
      parent_job_id: "job-1",
      retry_count: 1,
      status: "pending",
      requested_by: "admin",
      start_date: "2026-05-01",
      end_date: "2026-05-03",
      data_complete_from: "2026-05-01",
      progress_total_days: 3,
      progress_completed_days: 0,
      progress_percent: 0,
      progress_message: "Backfill accodato.",
      error_detail: null,
      created_at: "2026-05-29T07:11:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.clearWikiConversationMetricsBackfillJobHistory.mockResolvedValue({
      deleted_count: 1,
    });
  });

  test("renders governance settings and triggers save/backfill/retry/clear", async () => {
    render(<WikiConversationGovernanceSettingsPage />);

    await screen.findByText("Impostazioni conversazioni Wiki");
    expect(screen.getByText("Chain totali")).toBeInTheDocument();
    expect(screen.getAllByText("1").length).toBeGreaterThan(0);

    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[0], { target: { value: "3" } });
    fireEvent.click(screen.getByText("Salva soglie"));

    await waitFor(() => {
      expect(mocks.updateWikiConversationGovernanceConfig).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByText("Apri dettaglio"));
    await waitFor(() => {
      expect(mocks.getWikiConversationMetricsBackfillJobChainDetail).toHaveBeenCalledWith("token", "job-1");
      expect(screen.getByText(/Dettaglio chain/i)).toBeInTheDocument();
      expect(screen.getByText(/Riprova ultimo tentativo/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Riprova ultimo tentativo" }));
    await waitFor(() => {
      expect(mocks.retryWikiConversationMetricsBackfillJob).toHaveBeenCalledWith("token", "job-1");
      expect(screen.getByText(/retry di job-1/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Accoda backfill" }));
    await waitFor(() => {
      expect(mocks.enqueueWikiConversationMetricsBackfill).toHaveBeenCalled();
      expect(screen.getByText("Data complete from:")).toBeInTheDocument();
      expect(screen.getByText(/Job attuale/i)).toBeInTheDocument();
      expect(screen.getByText(/Chain queue/i)).toBeInTheDocument();
      expect(screen.getByText(/Chain 2 tentativi/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Pulisci storico" }));
    await waitFor(() => {
      expect(mocks.clearWikiConversationMetricsBackfillJobHistory).toHaveBeenCalledWith("token");
    });

    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[0], { target: { value: "failed" } });
    await waitFor(() => {
      expect(mocks.getWikiConversationMetricsBackfillJobChainSummary).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({ latestStatus: "failed", sortBy: "failed_first" }),
      );
      expect(mocks.listWikiConversationMetricsBackfillJobChains).toHaveBeenCalledWith(
        "token",
        6,
        expect.objectContaining({ latestStatus: "failed", sortBy: "failed_first" }),
      );
    });

    fireEvent.change(selects[1], { target: { value: "active" } });
    await waitFor(() => {
      expect(mocks.listWikiConversationMetricsBackfillJobChains).toHaveBeenCalledWith(
        "token",
        6,
        expect.objectContaining({ hasActiveRetry: true, sortBy: "failed_first" }),
      );
    });

    fireEvent.change(selects[2], { target: { value: "oldest_active_first" } });
    await waitFor(() => {
      expect(mocks.listWikiConversationMetricsBackfillJobChains).toHaveBeenCalledWith(
        "token",
        6,
        expect.objectContaining({ sortBy: "oldest_active_first" }),
      );
    });
  });
});
