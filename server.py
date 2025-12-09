from flask import Flask, render_template, request, jsonify, url_for, send_file
import cv2
import numpy as np
import base64
import time
import os
from threading import Lock
import datetime
import socket

import pandas as pd

app = Flask(__name__)


class SharedState:
    def __init__(self):
        self.current_frame1 = None
        self.current_frame2 = None
        self.current_frame = None  # OneCam Advanced 프레임 저장
        self.cpp_frame = None
        self.rpi_frame = None  # 라즈베리 파이 프레임 저장
        self.monitor_image = None  # 모니터링 프로그램 이미지 저장
        self.monitor_label = ""
        self.monitor_percentage = 0.0
        self.monitor_timestamp = ""
        self.face_count = 0
        self.cumulative_face_count = 0  # 누적된 Face Count 저장
        self.body_count = 0  # 바디 카운트
        self.cumulative_body_count = 0  # 누적된 Body Count 저장
        self.video_play_time = 0
        self.cumulative_video_play_time = 0  # 누적된 Video Play Time 저장
        self.cpp_object_count = 0
        self.cpp_percentage = 0
        self.cpp_cumulative_count = 0
        self.excel_data_onecam = []
        self.excel_data_cpp = []
        self.excel_data_rpi = []
        self.excel_data_monitor = []
        self.excel_data_onecam_advance = []  # OneCam Advanced 로그 데이터 추가
        self.video_start_time = None
        self.video_playing = False  # 비디오 재생 상태 저장
        self.start_time = time.time()
        self.last_data_update = time.time()  # 마지막 데이터 업데이트 시간
        self.lock = Lock()


state = SharedState()

# 소켓 경로 설정
SOCKET_PATH = '/tmp/led_control_socket'


# 페이지 종료 시 로그 저장
@app.route('/log_page_exit', methods=['GET'])
def log_page_exit():
    page = request.args.get('page', 'unknown')

    with state.lock:
        if page == 'onecam':
            state.excel_data_onecam.append({
                'Event': 'Page Exit',
                'Face Count': state.face_count,
                'Video Play Time': state.video_play_time
            })
        elif page == 'object_detector':
            state.excel_data_cpp.append({
                'Event': 'Page Exit',
                'Object Count': state.cpp_object_count,
                'Percentage': state.cpp_percentage
            })
        elif page == 'rpi_cam':
            state.excel_data_rpi.append({
                'Event': 'Page Exit',
                'Face Count': state.face_count,
                'Body Count': state.body_count
            })
        elif page == 'onecam_advance':
            state.excel_data_onecam_advance.append({
                'Event': 'Page Exit',
                'Face Count': state.face_count,
                'Video Playing': state.video_playing,
                'Video Play Time': state.video_play_time
            })

    return jsonify({'status': 'success'})


# /control_led 엔드포인트 추가
@app.route('/control_led', methods=['POST'])
def control_led():
    percentage = int(request.form.get('percentage'))
    duration = int(request.form.get('time'))

    # C++ 프로그램에 명령 전송
    try:
        send_command_to_cpp(percentage, duration)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error sending command to C++ program: {e}")
        return jsonify({'status': 'failure', 'message': str(e)}), 500


# C++ 프로그램에 명령을 보내는 함수 추가
def send_command_to_cpp(percentage, duration):
    # Unix 도메인 소켓을 사용하여 통신
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(SOCKET_PATH)
        # 명령을 문자열로 전송 (예: "20 10")
        command = f"{percentage} {duration}"
        client.sendall(command.encode('utf-8'))
    except Exception as e:
        raise e
    finally:
        client.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/onecam')
def onecam():
    return render_template('onecam.html')


@app.route('/object_detector')
def object_detector():
    return render_template('object_detector.html')


@app.route('/rpi_cam')
def rpi_cam():
    return render_template('rpi_cam.html')


@app.route('/sound')
def sound():
    return render_template('sound.html')  # 새로운 모니터링 페이지


@app.route('/onecam_advance')
def onecam_advance():
    return render_template('onecam_advance.html')


# OneCam 프레임 업데이트 및 처리
@app.route('/update_frame', methods=['POST'])
def update_frame():
    try:
        file1 = request.files['frame1']
        file2 = request.files['frame2']
        npimg1 = np.frombuffer(file1.read(), np.uint8)
        npimg2 = np.frombuffer(file2.read(), np.uint8)

        with state.lock:
            state.current_frame1 = cv2.imdecode(npimg1, cv2.IMREAD_COLOR)
            state.current_frame2 = cv2.imdecode(npimg2, cv2.IMREAD_COLOR)
            state.face_count = int(request.form['face_count'])
            video_playing = request.form['video_playing'] == 'True'

            # 누적된 Face Count와 Video Play Time 업데이트
            state.cumulative_face_count += state.face_count

            current_time = time.time()
            if video_playing and state.video_start_time is None:
                state.video_start_time = current_time
            elif not video_playing and state.video_start_time is not None:
                elapsed = current_time - state.video_start_time
                state.video_play_time += elapsed
                state.cumulative_video_play_time += elapsed
                state.video_start_time = None

            # 로그 데이터 추가
            state.excel_data_onecam.append({
                'Face Count': state.face_count,
                'Cumulative Face Count': state.cumulative_face_count,
                'Video Play Time': state.video_play_time,
                'Cumulative Video Play Time': state.cumulative_video_play_time
            })

            state.last_data_update = current_time

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# Object Detector 프레임 업데이트 및 처리
@app.route('/update_cpp_frame', methods=['POST'])
def update_cpp_frame():
    try:
        file = request.files['image']
        npimg = np.frombuffer(file.read(), np.uint8)

        object_count = int(request.form['objectCount'])
        percentage = float(request.form['percentage'])

        with state.lock:
            state.cpp_frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            state.cpp_object_count = object_count
            state.cpp_percentage = percentage
            state.cpp_cumulative_count += object_count

            # 로그 데이터를 추가
            state.excel_data_cpp.append({
                'Object Count': object_count,
                'Percentage': percentage,
                'Cumulative Count': state.cpp_cumulative_count
            })

            state.last_data_update = time.time()

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# Object Detector 누적 카운트 가져오기
@app.route('/get_cpp_cumulative_count')
def get_cpp_cumulative_count():
    with state.lock:
        return jsonify({
            "status": "success",
            "cumulative_count": state.cpp_cumulative_count
        })


# 라즈베리 파이 카메라 프레임 업데이트 및 처리
@app.route('/update_rpi_frame', methods=['POST'])
def update_rpi_frame():
    try:
        file = request.files['frame']
        npimg = np.frombuffer(file.read(), np.uint8)

        face_count = int(request.form['face_count'])
        body_count = int(request.form['body_count'])  # 바디 카운트 추가

        with state.lock:
            state.rpi_frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            state.face_count = face_count
            state.body_count = body_count

            # 누적된 Face Count와 Body Count 업데이트
            state.cumulative_face_count += face_count
            state.cumulative_body_count += body_count

            # 로그 데이터 추가
            state.excel_data_rpi.append({
                'Face Count': face_count,
                'Body Count': body_count,
                'Cumulative Face Count': state.cumulative_face_count,
                'Cumulative Body Count': state.cumulative_body_count
            })

            state.last_data_update = time.time()

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# 모니터링 프로그램 데이터 업데이트 엔드포인트
# 모니터링 프로그램 데이터 업데이트 엔드포인트 (개선 버전)
@app.route('/monitor_update', methods=['POST'])
def monitor_update():
    try:
        data = request.get_json()
        label = data.get('label', '')
        percentage = float(data.get('percentage', 0.0))
        image_data = data.get('image_data', '')

        # 이미지 데이터가 유효한지 확인
        if not image_data:
            # 이미지 데이터가 없으면 기본 이미지 또는 이전 이미지 유지
            with state.lock:
                state.monitor_label = label
                state.monitor_percentage = percentage
                # 로그 데이터 추가
                state.excel_data_monitor.append({
                    'Label': label,
                    'Percentage': percentage,
                    'Has Image': False
                })
                state.last_data_update = time.time()

            print(f"이미지 데이터 없음: {label}, {percentage}%")
            return jsonify({"status": "success", "message": "No image data"})

        try:
            # 이미지 디코딩 시도
            image_bytes = base64.b64decode(image_data)
            npimg = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

            # 이미지 디코딩 실패 확인
            if image is None:
                print(f"이미지 디코딩 실패: 유효하지 않은 이미지 데이터")
                return jsonify({"status": "error", "message": "Invalid image data"}), 400

            with state.lock:
                state.monitor_image = image
                state.monitor_label = label
                state.monitor_percentage = percentage
                # 로그 데이터 추가
                state.excel_data_monitor.append({
                    'Label': label,
                    'Percentage': percentage,
                    'Has Image': True
                })
                state.last_data_update = time.time()

            return jsonify({"status": "success"})
        except Exception as e:
            print(f"이미지 처리 오류: {e}")
            return jsonify({"status": "error", "message": f"Image processing error: {str(e)}"}), 400

    except Exception as e:
        print(f"모니터링 업데이트 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


# OneCam Advanced 프레임 업데이트
@app.route('/update_onecam_advance_frame', methods=['POST'])
def update_onecam_advance_frame():
    try:
        data = request.get_json()
        face_count = int(data.get('face_count', 0))
        video_playing = data.get('video_playing') == 'True'
        frame_data = data.get('frame_data')

        if frame_data:
            # 프레임 디코딩
            frame_bytes = base64.b64decode(frame_data)
            npimg = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        else:
            frame = None

        with state.lock:
            state.face_count = face_count
            state.video_playing = video_playing
            if frame is not None:
                state.current_frame = frame

            current_time = time.time()
            # 누적된 Face Count와 Video Play Time 업데이트
            state.cumulative_face_count += face_count

            if video_playing and state.video_start_time is None:
                state.video_start_time = current_time
            elif not video_playing and state.video_start_time is not None:
                elapsed = current_time - state.video_start_time
                state.video_play_time += elapsed
                state.cumulative_video_play_time += elapsed
                state.video_start_time = None

            # 로그 데이터 추가
            state.excel_data_onecam_advance.append({
                'Face Count': face_count,
                'Cumulative Face Count': state.cumulative_face_count,
                'Video Playing': video_playing,
                'Video Play Time': state.video_play_time,
                'Cumulative Video Play Time': state.cumulative_video_play_time
            })

            state.last_data_update = current_time

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# OneCam 프레임 가져오기
@app.route('/get_frame')
def get_frame():
    with state.lock:
        if state.current_frame1 is None:
            return jsonify({"status": "no frame"})

        current_frame = state.current_frame1 if state.video_start_time is None else state.current_frame2

        _, buffer = cv2.imencode('.jpg', current_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        current_time = time.time()
        uptime = current_time - state.start_time

        # 비디오가 재생 중인 경우 실시간으로 재생 시간 계산
        if state.video_start_time:
            video_play_time = state.video_play_time + (current_time - state.video_start_time)
        else:
            video_play_time = state.video_play_time

        return jsonify({
            "status": "success",
            "frame": frame_base64,
            "face_count": state.face_count,
            "cumulative_face_count": state.cumulative_face_count,  # 누적된 Face Count 반환
            "uptime": uptime,
            "video_play_time": video_play_time,
            "cumulative_video_play_time": state.cumulative_video_play_time  # 누적된 Video Play Time 반환
        })


# Object Detector 프레임 가져오기
@app.route('/get_cpp_frame')
def get_cpp_frame():
    with state.lock:
        if state.cpp_frame is None:
            return jsonify({"status": "no frame"})

        _, buffer = cv2.imencode('.jpg', state.cpp_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            "status": "success",
            "cpp_frame": frame_base64,
            "object_count": state.cpp_object_count,
            "percentage": state.cpp_percentage,
            "cumulative_count": state.cpp_cumulative_count  # 누적 카운트 추가
        })


# 라즈베리 파이 카메라 프레임 가져오기
@app.route('/get_rpi_frame')
def get_rpi_frame():
    with state.lock:
        if state.rpi_frame is None:
            return jsonify({"status": "no frame"})

        _, buffer = cv2.imencode('.jpg', state.rpi_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            "status": "success",
            "frame": frame_base64,
            "face_count": state.face_count,
            "cumulative_face_count": state.cumulative_face_count,  # 누적된 Face Count 반환
            "body_count": state.body_count,  # 바디 카운트 반환
            "cumulative_body_count": state.cumulative_body_count  # 누적된 Body Count 반환
        })


# 모니터링 프로그램 프레임 가져오기
@app.route('/get_monitor_frame')
def get_monitor_frame():
    with state.lock:
        if state.monitor_image is None:
            return jsonify({"status": "no frame"})

        try:
            # 이미지 인코딩 시도
            _, buffer = cv2.imencode('.jpg', state.monitor_image)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')

            return jsonify({
                "status": "success",
                "image": frame_base64,
                "label": state.monitor_label,
                "percentage": state.monitor_percentage
            })
        except Exception as e:
            print(f"이미지 인코딩 오류: {e}")
            # 오류 발생 시 상태만 반환하고 이미지는 보내지 않음
            return jsonify({
                "status": "success",
                "image": None,
                "label": state.monitor_label,
                "percentage": state.monitor_percentage,
                "error": str(e)
            })


# OneCam Advanced 프레임 가져오기
@app.route('/get_onecam_advance_frame')
def get_onecam_advance_frame():
    with state.lock:
        current_time = time.time()

        if state.current_frame is not None:
            _, buffer = cv2.imencode('.jpg', state.current_frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
        else:
            frame_base64 = None

        uptime = current_time - state.start_time

        # 비디오가 재생 중인 경우 실시간으로 재생 시간 계산
        if state.video_playing and state.video_start_time:
            video_play_time = state.video_play_time + (current_time - state.video_start_time)
        else:
            video_play_time = state.video_play_time

        return jsonify({
            "status": "success",
            "frame": frame_base64,
            "face_count": state.face_count,
            "cumulative_face_count": state.cumulative_face_count,
            "video_playing": str(state.video_playing),
            "uptime": uptime,
            "video_play_time": video_play_time,
            "cumulative_video_play_time": state.cumulative_video_play_time
        })


# 로그 데이터 내보내기 (OneCam)
@app.route('/export_data')
def export_data():
    with state.lock:
        # 로그 내보내기 전에 현재 상태 저장
        state.excel_data_onecam.append({
            'Event': 'Export Log',
            'Face Count': state.face_count,
            'Cumulative Face Count': state.cumulative_face_count,
            'Video Play Time': state.video_play_time,
            'Cumulative Video Play Time': state.cumulative_video_play_time
        })

        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_onecam_log.xlsx"
        filepath = os.path.join('logs', filename)
        os.makedirs('logs', exist_ok=True)
        df = pd.DataFrame(state.excel_data_onecam)
        df.to_excel(filepath, index=False)
    return jsonify({"status": "success", "filename": filename})


# 로그 데이터 내보내기 (Object Detector)
@app.route('/export_cpp_data')
def export_cpp_data():
    with state.lock:
        # 로그 내보내기 전에 현재 상태 저장
        state.excel_data_cpp.append({
            'Event': 'Export Log',
            'Object Count': state.cpp_object_count,
            'Percentage': state.cpp_percentage,
            'Cumulative Count': state.cpp_cumulative_count
        })

        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_object_detector_log.xlsx"
        filepath = os.path.join('logs', filename)
        os.makedirs('logs', exist_ok=True)
        df = pd.DataFrame(state.excel_data_cpp)
        df.to_excel(filepath, index=False)
    return jsonify({"status": "success", "filename": filename})


# 로그 데이터 내보내기 (라즈베리 파이 카메라)
@app.route('/export_rpi_data')
def export_rpi_data():
    with state.lock:
        # 로그 내보내기 전에 현재 상태 저장
        state.excel_data_rpi.append({
            'Event': 'Export Log',
            'Face Count': state.face_count,
            'Body Count': state.body_count,
            'Cumulative Face Count': state.cumulative_face_count,
            'Cumulative Body Count': state.cumulative_body_count
        })

        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_rpi_cam_log.xlsx"
        filepath = os.path.join('logs', filename)
        os.makedirs('logs', exist_ok=True)
        df = pd.DataFrame(state.excel_data_rpi)
        df.to_excel(filepath, index=False)
    return jsonify({"status": "success", "filename": filename})


# 로그 데이터 내보내기 (모니터링 프로그램)
@app.route('/export_monitor_data')
def export_monitor_data():
    with state.lock:
        # OneCam Advance 페이지에서 요청한 경우
        if request.referrer and 'onecam_advance' in request.referrer:
            # 로그 내보내기 전에 현재 상태 저장
            state.excel_data_onecam_advance.append({
                'Event': 'Export Log',
                'Face Count': state.face_count,
                'Cumulative Face Count': state.cumulative_face_count,
                'Video Playing': state.video_playing,
                'Video Play Time': state.video_play_time,
                'Cumulative Video Play Time': state.cumulative_video_play_time
            })

            filename = f"{time.strftime('%Y%m%d_%H%M%S')}_onecam_advance_log.xlsx"
            filepath = os.path.join('logs', filename)
            os.makedirs('logs', exist_ok=True)
            df = pd.DataFrame(state.excel_data_onecam_advance)
            df.to_excel(filepath, index=False)
        else:
            # 기존 모니터링 로그 내보내기
            state.excel_data_monitor.append({
                'Event': 'Export Log',
                'Label': state.monitor_label,
                'Percentage': state.monitor_percentage
            })

            filename = f"{time.strftime('%Y%m%d_%H%M%S')}_monitor_log.xlsx"
            filepath = os.path.join('logs', filename)
            os.makedirs('logs', exist_ok=True)
            df = pd.DataFrame(state.excel_data_monitor)
            df.to_excel(filepath, index=False)

    return jsonify({"status": "success", "filename": filename})


# 카운터 리셋 (OneCam)
@app.route('/reset_counter')
def reset_counter():
    with state.lock:
        state.excel_data_onecam.append({
            'Event': 'Reset Counter',
            'Face Count': state.face_count,
            'Cumulative Face Count': state.cumulative_face_count,
            'Video Play Time': state.video_play_time,
            'Cumulative Video Play Time': state.cumulative_video_play_time
        })
        state.face_count = 0
        state.cumulative_face_count = 0  # 누적된 Face Count 리셋
        state.video_play_time = 0
        state.cumulative_video_play_time = 0  # 누적된 Video Play Time 리셋
        state.video_start_time = None
    return jsonify({"status": "success"})


# 카운터 리셋 (Object Detector)
@app.route('/reset_cpp_counter')
def reset_cpp_counter():
    with state.lock:
        state.excel_data_cpp.append({
            'Event': 'Reset Counter',
            'Object Count': state.cpp_object_count,
            'Percentage': state.cpp_percentage,
            'Cumulative Count': state.cpp_cumulative_count
        })
        state.cpp_cumulative_count = 0
    return jsonify({"status": "success"})


# 카운터 리셋 (라즈베리 파이 카메라)
@app.route('/reset_rpi_counter')
def reset_rpi_counter():
    with state.lock:
        state.excel_data_rpi.append({
            'Event': 'Reset Counter',
            'Face Count': state.face_count,
            'Body Count': state.body_count,
            'Cumulative Face Count': state.cumulative_face_count,
            'Cumulative Body Count': state.cumulative_body_count
        })
        state.face_count = 0
        state.body_count = 0
        state.cumulative_face_count = 0  # 누적된 Face Count 리셋
        state.cumulative_body_count = 0  # 누적된 Body Count 리셋
    return jsonify({"status": "success"})


# 카운터 리셋 (모니터링 프로그램)
@app.route('/reset_monitor_counter')
def reset_monitor_counter():
    with state.lock:
        state.excel_data_monitor.append({
            'Event': 'Reset Counter',
            'Label': state.monitor_label,
            'Percentage': state.monitor_percentage
        })
        state.monitor_label = ""
        state.monitor_percentage = 0.0
        state.monitor_timestamp = ""
    return jsonify({"status": "success"})


# 날씨 정보 페이지
@app.route('/weather')
def weather_view():
    return render_template('weather.html')


weather_data = {
    "temperature": "데이터 없음",
    "humidity": "데이터 없음",
    "weather": "데이터 없음",
    "precipitation": "0",
    "snowfall": "0"
}

log_file = "weather_log.txt"
last_weather_data = None  # 서버에서 마지막으로 받은 데이터를 저장


@app.route('/get_weather_data', methods=['GET'])
def get_weather_data():
    return jsonify(weather_data)


@app.route('/get_last_weather_data', methods=['GET'])
def get_last_weather_data():
    global last_weather_data
    if last_weather_data is not None:
        return jsonify(last_weather_data)
    else:
        return jsonify({
            "temperature": "데이터 없음",
            "humidity": "데이터 없음",
            "weather": "데이터 없음",
            "precipitation": "0",
            "snowfall": "0"
        })


@app.route('/update_weather_data', methods=['POST'])
def update_weather_data():
    global last_weather_data
    data = request.json
    last_weather_data = data  # 최신 데이터를 갱신
    # 기존의 로그 파일에 저장하는 코드도 추가
    with open(log_file, 'a') as file:
        file.write(
            f"온도: {data['temperature']}°C, 습도: {data['humidity']}%, 날씨: {data['weather']}, 강수량: {data['precipitation']}mm, 적설량: {data['snowfall']}cm\n")
    return jsonify({"status": "success"})


@app.route('/export_weather_log', methods=['GET'])
def export_weather_log():
    return send_file(log_file, as_attachment=True)


# 주기적으로 세션 상태를 데이터에 기록하는 백그라운드 스레드 함수
def background_data_logger():
    import threading
    import time

    def log_data_periodically():
        while True:
            try:
                with state.lock:
                    current_time = time.time()
                    # 마지막 데이터 업데이트 후 60초가 지났을 때만 로깅
                    if current_time - state.last_data_update > 60:
                        # OneCam 데이터 로깅
                        if state.current_frame1 is not None:
                            state.excel_data_onecam.append({
                                'Event': 'Background Log',
                                'Face Count': state.face_count,
                                'Cumulative Face Count': state.cumulative_face_count,
                                'Video Play Time': state.video_play_time,
                                'Cumulative Video Play Time': state.cumulative_video_play_time
                            })

                        # Object Detector 데이터 로깅
                        if state.cpp_frame is not None:
                            state.excel_data_cpp.append({
                                'Event': 'Background Log',
                                'Object Count': state.cpp_object_count,
                                'Percentage': state.cpp_percentage,
                                'Cumulative Count': state.cpp_cumulative_count
                            })

                        # 라즈베리 파이 카메라 데이터 로깅
                        if state.rpi_frame is not None:
                            state.excel_data_rpi.append({
                                'Event': 'Background Log',
                                'Face Count': state.face_count,
                                'Body Count': state.body_count,
                                'Cumulative Face Count': state.cumulative_face_count,
                                'Cumulative Body Count': state.cumulative_body_count
                            })

                        # OneCam Advanced 데이터 로깅
                        if state.current_frame is not None:
                            state.excel_data_onecam_advance.append({
                                'Event': 'Background Log',
                                'Face Count': state.face_count,
                                'Cumulative Face Count': state.cumulative_face_count,
                                'Video Playing': state.video_playing,
                                'Video Play Time': state.video_play_time,
                                'Cumulative Video Play Time': state.cumulative_video_play_time
                            })

                        state.last_data_update = current_time

                # 5분(300초)마다 실행
                time.sleep(300)
            except Exception as e:
                print(f"Background logging error: {e}")
                time.sleep(60)  # 오류 발생 시 1분 후 재시도

    # 백그라운드 스레드 시작
    background_thread = threading.Thread(target=log_data_periodically)
    background_thread.daemon = True  # 메인 스레드가 종료되면 함께 종료
    background_thread.start()


# 서버 시작 시 백그라운드 로거 시작
if __name__ == '__main__':
    background_data_logger()  # 백그라운드 데이터 로깅 시작
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
