"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Download, Scissors } from "lucide-react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [loading, setLoading] = useState(false);
  const [clipId, setClipId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setClipId(null);

    try {
      const response = await fetch("http://localhost:8000/api/v1/clip/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
          start_time: startTime,
          end_time: endTime,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail?.message || "Failed to create clip");
      }

      setClipId(data.clip_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (clipId) {
      window.open(`http://localhost:8000/api/v1/clip/download/${clipId}`, "_blank");
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-4 md:p-8">
      <div className="mx-auto max-w-4xl space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight">YouTube Clipper</h1>
          <p className="text-muted-foreground text-lg">
            Extract perfect clips from your favorite YouTube videos
          </p>
        </div>

        <Card className="border-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scissors className="h-5 w-5" />
              Create New Clip
            </CardTitle>
            <CardDescription>
              Enter the YouTube URL and specify the start and end times for your clip
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="url" className="text-sm font-medium">
                    YouTube URL
                  </label>
                  <Input
                    id="url"
                    type="url"
                    placeholder="https://www.youtube.com/watch?v=..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    required
                    className="h-12"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label htmlFor="startTime" className="text-sm font-medium">
                      Start Time (HH:MM:SS)
                    </label>
                    <Input
                      id="startTime"
                      placeholder="00:00:00"
                      value={startTime}
                      onChange={(e) => setStartTime(e.target.value)}
                      required
                      pattern="^(\d{1,2}:)?(\d{1,2}):(\d{2})(\.\d+)?$"
                      className="h-12"
                    />
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="endTime" className="text-sm font-medium">
                      End Time (HH:MM:SS)
                    </label>
                    <Input
                      id="endTime"
                      placeholder="00:00:00"
                      value={endTime}
                      onChange={(e) => setEndTime(e.target.value)}
                      required
                      pattern="^(\d{1,2}:)?(\d{1,2}):(\d{2})(\.\d+)?$"
                      className="h-12"
                    />
                  </div>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full h-12"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating Clip...
                  </>
                ) : (
                  <>
                    <Scissors className="mr-2 h-4 w-4" />
                    Create Clip
                  </>
                )}
              </Button>
            </form>

            {error && (
              <div className="mt-4 p-4 bg-destructive/10 text-destructive rounded-lg">
                {error}
              </div>
            )}

            {clipId && (
              <div className="mt-6 p-4 bg-primary/10 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Clip created successfully!</p>
                    <p className="text-sm text-muted-foreground">
                      Your clip is ready to download
                    </p>
                  </div>
                  <Button onClick={handleDownload} className="gap-2">
                    <Download className="h-4 w-4" />
                    Download
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">How to Use</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>1. Paste a YouTube video URL</p>
              <p>2. Enter start and end times in HH:MM:SS format</p>
              <p>3. Click Create Clip and wait for processing</p>
              <p>4. Download your clip when ready</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Tips</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>• Use MM:SS format for clips under an hour</p>
              <p>• Clips are saved locally for easy access</p>
              <p>• You can create multiple clips from the same video</p>
              <p>• Maximum clip duration is 1 hour</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
