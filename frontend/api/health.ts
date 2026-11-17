import handler, { handleProxy } from "./[...path]";

export default async function healthHandler(req: any, res: any) {
  return handleProxy(req, res, "/health");
}
