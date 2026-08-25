import * as tus from "tus-js-client";
import { supabase } from "./supabase";

type UploadOptions = {
  file: File;
  sessionId: string;
  onProgress?: (percentage: number) => void;
};

export async function uploadRaceVideo({
  file,
  sessionId,
  onProgress,
}: UploadOptions): Promise<string> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.user || !session.access_token) {
    throw new Error("Your session expired. Please sign in again.");
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  if (!supabaseUrl || !publishableKey) {
    throw new Error("Supabase environment variables are missing.");
  }

  const projectRef = new URL(supabaseUrl).hostname.split(".")[0];
  const storageEndpoint =
    `https://${projectRef}.storage.supabase.co/storage/v1/upload/resumable`;

  const extension = file.name.split(".").pop()?.toLowerCase() || "mp4";
  const objectPath =
    `${session.user.id}/${sessionId}/original-video.${extension}`;

  return new Promise((resolve, reject) => {
    const upload = new tus.Upload(file, {
      endpoint: storageEndpoint,

      headers: {
        authorization: `Bearer ${session.access_token}`,
        apikey: publishableKey,
      },

      metadata: {
        bucketName: "race-videos",
        objectName: objectPath,
        contentType: file.type || "video/mp4",
        cacheControl: "3600",
      },

      chunkSize: 6 * 1024 * 1024,
      retryDelays: [0, 1000, 3000, 5000, 10000],
      removeFingerprintOnSuccess: true,

      onError(error) {
        reject(new Error(`Video upload failed: ${error.message}`));
      },

      onProgress(uploadedBytes, totalBytes) {
        const percentage = Math.round(
          (uploadedBytes / totalBytes) * 100
        );

        onProgress?.(percentage);
      },

      onSuccess() {
        resolve(objectPath);
      },
    });

    upload.findPreviousUploads().then((previousUploads) => {
      if (previousUploads.length > 0) {
        upload.resumeFromPreviousUpload(previousUploads[0]);
      }

      upload.start();
    }).catch(reject);
  });
}