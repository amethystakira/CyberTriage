        <option>Analyzing</option>
        <option>Completed</option>
      </select>
    </div>

    {isLoading ? (
      <p>Loading investigations...</p>
    ) : filteredCases.length === 0 ? (
      <p>No matching investigations found.</p>
    ) : (
      <div className="investigation-table-wrapper">
        <table className="investigation-table">
          <thead>
            <tr>
              <th>Case ID</th>
              <th>Investigation</th>
              <th>Investigator</th>
              <th>Date Created</th>
              <th>Severity</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {filteredCases.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.name}</td>
                <td>{item.investigator}</td>
                <td>{item.date}</td>
                <td>{item.severity}</td>
                <td>{item.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </section>
) : null}
        </section>
      </main>

      {caseModalOpen && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setCaseModalOpen(false);
            }
          }}
        >
          <form className="case-dialog" onSubmit={createCase}>
            <div className="panel-heading">
              <div>
                <h3>New Investigation</h3>
                <p>Create a case in your local investigation database.</p>
              </div>

              <button
                type="button"
                className="icon-button"
                aria-label="Close"
                onClick={() => setCaseModalOpen(false)}
              >
                <X size={19} />
              </button>
            </div>

            <label className="case-form-label" htmlFor="case-name">
              Investigation name
            </label>

            <input
              id="case-name"
              className="case-form-input"
              autoFocus
              required
              maxLength={200}
              value={caseName}
              onChange={(event) => setCaseName(event.target.value)}
              placeholder="e.g. Suspicious login activity"
            />

            {caseError && (
              <p className="form-error" role="alert">
                {caseError}
              </p>
            )}

            <div className="dialog-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setCaseModalOpen(false)}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="primary-button"
                disabled={isSaving}
              >
                {isSaving ? "Creating…" : "Create Investigation"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default App;
