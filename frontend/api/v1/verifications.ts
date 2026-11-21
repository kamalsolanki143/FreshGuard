import { handleProxy, VercelRequest, VercelResponse } from "../_lib/proxy";

export default async function verificationsHandler(req: VercelRequest, res: VercelResponse) {
  return handleProxy(req, res, "/v1/verifications");
}
