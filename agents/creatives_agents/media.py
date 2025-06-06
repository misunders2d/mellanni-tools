# import moviepy.editor as mp
# from PIL import Image

# def resize_image(image_path, output_size=(1080, 1920)):
#     """Resize an image to the specified output size while maintaining aspect ratio."""
#     img = Image.open(image_path)
#     img = img.resize(output_size, Image.Resampling.LANCZOS)
#     img.save(image_path)  # Overwrite the original image
#     return image_path

# def create_tiktok_video(image_paths, audio_track_path, voiceover_path, captions_data, output_path):
#     """Create a TikTok video from images, audio, voiceover, and captions."""
#     # Step 1: Resize images to 1080x1920
#     for image_path in image_paths:
#         resize_image(image_path)

#     # Step 2: Create image slideshow
#     image_duration = 5  # Duration per image in seconds
#     clips = [mp.ImageClip(img, duration=image_duration) for img in image_paths]
#     video = mp.concatenate_videoclips(clips, method="compose")

#     # Step 3: Combine audio track and voiceover using moviepy
#     audio_track = mp.AudioFileClip(audio_track_path)
#     voiceover = mp.AudioFileClip(voiceover_path)
#     # Lower background track volume to 50%
#     audio_track = audio_track.volumex(0.5)  # Reduce volume by 50%
#     # Mix audio: overlay voiceover on background track
#     combined_audio = mp.CompositeAudioClip([audio_track, voiceover])
#     # Set video duration to match audio duration
#     video = video.set_duration(combined_audio.duration)

#     # Step 4: Add captions
#     caption_clips = []
#     for caption in captions_data:
#         txt_clip = mp.TextClip(
#             caption["text"],
#             fontsize=80,
#             color="gray",
#             stroke_color="pink",
#             stroke_width=2,
#             font="Arial-Bold",
#             size=(video.w, None),
#             method="caption",
#             align="center"
#         )
#         txt_clip = txt_clip.set_position(("center", video.h * 0.8))  # Bottom 20% of the video
#         txt_clip = txt_clip.set_start(caption["start_time"]).set_end(caption["end_time"])
#         caption_clips.append(txt_clip)

#     # Step 5: Combine video, audio, and captions
#     final_video = mp.CompositeVideoClip([video] + caption_clips)
#     final_video = final_video.set_audio(combined_audio)

#     # Step 6: Export the video
#     final_video.write_videofile(
#         output_path,
#         codec="libx264",
#         audio_codec="aac",
#         fps=24,
#         preset="medium"
#     )

# if __name__ == "__main__":
#     # Example inputs
#     image_paths = [
#         '/home/misunderstood/Downloads/img2/image1_0.png',
#         '/home/misunderstood/Downloads/img2/image2_0.png',
#         '/home/misunderstood/Downloads/img2/image3_0.png',
#         '/home/misunderstood/Downloads/img2/image4_0.png',
#         ]
#     audio_track_path = '/home/misunderstood/temp/music/music2.wav'  # Replace with your audio track
#     voiceover_path = '/home/misunderstood/temp/music/speech.wav'  # Replace with your voiceover
#     captions_data = [
#         {"text": "Welcome to my TikTok!", "start_time": 0, "end_time": 5},
#         {"text": "Check out these cool images!", "start_time": 5, "end_time": 10},
#         {"text": "Hope you enjoyed!", "start_time": 10, "end_time": 15}
#     ]  # Replace with your captions and timestamps
#     output_path = "tiktok_video.mp4"

#     create_tiktok_video(image_paths, audio_track_path, voiceover_path, captions_data, output_path)
