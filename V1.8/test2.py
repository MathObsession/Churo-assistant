import subprocess

# 1. Define a smaller target width (try values between 30 and 60)
small_width = 60

# 2. Run chafa with the smaller size constraint
subprocess.run([
    "chafa",
    "/Users/lakshyaprajapati/Documents/Repositories/generated_image.png",
    "--symbols", "block",
    f"--size={small_width}"  # Shrinks the overall size
])
