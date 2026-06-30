// Shared API types live here, mirroring the backend Pydantic contracts
// (plan/01-data-model.md). Populated as endpoints land.

export interface Health {
  status: string;
  version: string;
  extract_model: string;
  verify_model: string;
}
