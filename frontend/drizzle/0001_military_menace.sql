CREATE TABLE "video_downloads" (
	"video_id" text PRIMARY KEY NOT NULL,
	"file_path" text NOT NULL,
	"file_size" integer,
	"duration" integer,
	"downloaded_at" timestamp DEFAULT now() NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL
);
