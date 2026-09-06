"use client";

import { useState } from "react";
import { IconReset } from "@/app/icons";
import { resetLabAction, resetAllAction } from "@/app/actions";

export function ResetLabButton({ id, title }: { id: string; title: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        className="btn ghost"
        style={{ width: "100%", marginTop: 14 }}
        onClick={() => setOpen(true)}
      >
        Reset this lab
      </button>
      {open && (
        <div
          className="modal-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false);
          }}
        >
          <div className="modal">
            <div className="m-ic">
              <IconReset />
            </div>
            <h3>Reset this lab?</h3>
            <p>
              Your progress for <b>Lab {id} &mdash; {title}</b> (solved status and attempts) will be
              cleared, so you can start it fresh.
            </p>
            <div className="modal-actions">
              <button type="button" className="btn ghost" onClick={() => setOpen(false)}>
                Cancel
              </button>
              <form action={resetLabAction}>
                <input type="hidden" name="id" value={id} />
                <button className="btn" type="submit">
                  Reset lab
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function ResetAllButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className="btn ghost" onClick={() => setOpen(true)}>
        Reset all progress
      </button>
      {open && (
        <div
          className="modal-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false);
          }}
        >
          <div className="modal">
            <div className="m-ic">
              <IconReset />
            </div>
            <h3>Reset all progress?</h3>
            <p>Every lab&apos;s solved status and attempts will be cleared. This cannot be undone.</p>
            <div className="modal-actions">
              <button type="button" className="btn ghost" onClick={() => setOpen(false)}>
                Cancel
              </button>
              <form action={resetAllAction}>
                <button className="btn" type="submit">
                  Reset all
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
