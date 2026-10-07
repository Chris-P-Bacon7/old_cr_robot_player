from ultralytics import YOLO
import cv2
import os

model_path = "runs\\detect\\train8w\\weights\\best.pt"

if __name__ == "__main__":

    if not os.path.exists(model_path):
        print(f"Error: Could not find model at {model_path}.")

    model = YOLO(model_path)

    img_path = "assets\\raw_images\\Game_4\\clash_gameplay_44.png"
    print(f"Looking at {img_path}...")
    results = model(img_path)
    
    print("Press 'q' to close the window")

    cv2.namedWindow("YOLO Vision", cv2.WINDOW_NORMAL)

    while True:
        # window_size = input("What window size would you like (small/large): ")
        window_size = "small"
        if window_size.lower() == "large":
            cv2.resizeWindow("YOLO Vision", 450, 954)
            break
        elif window_size.lower() == "small":
            cv2.resizeWindow("YOLO Vision", 375, 800)
            break
        else:
            print("Invalid input. Try again.")

    while True:
        for result in results:
            annotated_frame = result.plot()
            cv2.imshow("YOLO Vision", annotated_frame)

        if cv2.waitKey(1) == ord('q'): 
            break
        
    cv2.destroyAllWindows