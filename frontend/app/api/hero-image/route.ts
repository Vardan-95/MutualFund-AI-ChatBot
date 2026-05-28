import { readFile } from "node:fs/promises";
import { NextResponse } from "next/server";

const CANDIDATE_PATHS = [
  process.env.HERO_IMAGE_PATH || "",
  "C:\\Users\\HP\\.cursor\\projects\\e-AI-Projects-Mutual-fund\\assets\\c__Users_HP_AppData_Roaming_Cursor_User_workspaceStorage_766911bc9d33528b90501a77f39f413a_images_image-4230464f-e6b8-4202-b2fd-a428645cc6a3.png"
].filter(Boolean);

export async function GET() {
  for (const p of CANDIDATE_PATHS) {
    try {
      const buf = await readFile(p);
      return new NextResponse(buf, {
        headers: {
          "Content-Type": "image/png",
          "Cache-Control": "public, max-age=300"
        }
      });
    } catch {
      // try next candidate
    }
  }
  return new NextResponse("Hero image not found", { status: 404 });
}

