import { handleProxy } from "../[...path]";

export default async function verificationsHandler(req: any, res: any) {
  return handleProxy(req, res, "/v1/verifications");
}
