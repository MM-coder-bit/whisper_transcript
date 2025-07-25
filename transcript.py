import whisper
from datetime import timedelta
import os
import re
import yt_dlp
import ffmpeg
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import traceback
from datetime import datetime
import shutil
import time

def is_youtube_url(url):
    """Verifica se a entrada é uma URL válida do YouTube."""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube\.com|youtu\.be)/'
        r'(watch\?v=|v/|embed/|shorts/)?'
        r'([A-Za-z0-9_-]{11})'
    )
    return re.match(youtube_regex, url) is not None

def check_ffmpeg():
    """Verifica se o ffmpeg está instalado e retorna seu caminho."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        error_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro: ffmpeg não encontrado no PATH do sistema.\n"
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(error_message)
    return ffmpeg_path

def download_youtube_audio(url, output_path="audio_temp.wav", status_label=None):
    """Baixa o áudio de um vídeo do YouTube e o converte para WAV."""
    ffmpeg_path = check_ffmpeg()
    if ffmpeg_path is None:
        error_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro: ffmpeg não encontrado no PATH do sistema.\n"
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(error_message)
        raise Exception("ffmpeg não encontrado. Instale o ffmpeg e adicione ao PATH.")
    
    if status_label:
        #status_label.config(text=f"Usando ffmpeg em: {ffmpeg_path}")
        #status_label.update()
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Usando ffmpeg em: {ffmpeg_path}\n")

    try:
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': os.path.splitext(output_path)[0] + '.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': ffmpeg_path,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
    except Exception as e:
        error_details = traceback.format_exc()
        error_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro ao baixar ou converter áudio do YouTube: {str(e)}\nDetalhes: {error_details}\n"
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(error_message)
        raise Exception(f"Erro ao baixar ou converter áudio do YouTube: {str(e)}")

def format_srt_time(seconds):
    """Formata o tempo em segundos para o formato SRT (HH:MM:SS,mmm)."""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def transcribe_video(input_path, output_srt, language, model_size, status_label, initial_prompt=None):
    """Transcreve um vídeo local ou do YouTube e gera um arquivo SRT, medindo o tempo de execução."""
    try:
        status_label.config(text="Iniciando transcrição...")
        status_label.update()

        # Verifica se a entrada é uma URL do YouTube
        if is_youtube_url(input_path):
            status_label.config(text="Baixando áudio do YouTube...")
            status_label.update()
            audio_file = download_youtube_audio(input_path, status_label=status_label)
        else:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"O arquivo {input_path} não foi encontrado.")
            audio_file = input_path

        # Carrega o modelo Whisper
        status_label.config(text=f"Carregando modelo Whisper '{model_size}'...")
        status_label.update()
        model = whisper.load_model(model_size, device="cpu")

        # Inicia o temporizador
        start_time = time.time()
        
        # Define o prompt inicial (padrão se não fornecido)
        prompt = initial_prompt if initial_prompt else "Este áudio é em português e pode conter vocabulário técnico."
        
        # Realiza a transcrição
        status_label.config(text="Transcrevendo áudio...")
        status_label.update()
        result = model.transcribe(
            audio_file,
            language=language,
            word_timestamps=True,
            initial_prompt=prompt
        )

        # Gera o arquivo SRT
        status_label.config(text=f"Gerando arquivo SRT: {output_srt}")
        status_label.update()
        with open(output_srt, "w", encoding="utf-8") as f:
            for i, segment in enumerate(result["segments"], 1):
                start = format_srt_time(segment["start"])
                end = format_srt_time(segment["end"])
                text = segment["text"].strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

        # Finaliza o temporizador
        end_time = time.time()
        elapsed_time = end_time - start_time
        elapsed_time_formatted = str(timedelta(seconds=int(elapsed_time)))
        
        # Exibe o tempo de transcrição na interface e registra no log
        status_label.config(text=f"Transcrição concluída! Arquivo salvo em: {output_srt}. Tempo: {elapsed_time_formatted} ({elapsed_time:.2f} segundos)")
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Transcrição concluída em: {elapsed_time_formatted} ({elapsed_time:.2f} segundos)\n")

        if is_youtube_url(input_path):
            os.remove(audio_file)

    except Exception as e:
        error_details = traceback.format_exc()
        error_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro durante a transcrição: {str(e)}\nDetalhes: {error_details}\n"
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(error_message)
        status_label.config(text=f"Erro: {str(e)}")
        messagebox.showerror("Erro", f"Erro durante a transcrição: {str(e)}\nDetalhes salvos em error_log.txt")

def start_transcription(entry_path, output_entry, language_var, model_var, prompt_entry, status_label):
    """Inicia a transcrição em uma thread separada para evitar travamento da GUI."""
    input_path = entry_path.get()
    output_srt = output_entry.get() or "transcription.srt"
    language = language_var.get()
    model_size = model_var.get()
    initial_prompt = prompt_entry.get().strip() or None  # Usa None se o campo estiver vazio

    if not input_path:
        messagebox.showwarning("Aviso", "Por favor, insira um caminho de vídeo ou URL do YouTube.")
        return

    threading.Thread(
        target=transcribe_video,
        args=(input_path, output_srt, language, model_size, status_label, initial_prompt),
        daemon=True
    ).start()

def browse_file(entry_path):
    """Abre um diálogo para selecionar um arquivo de vídeo local."""
    file_path = filedialog.askopenfilename(
        filetypes=[("Arquivos de vídeo", "*.mp4 *.avi *.mkv *.mov *.wmv")]
    )
    if file_path:
        entry_path.delete(0, tk.END)
        entry_path.insert(0, file_path)

def create_gui():
    """Cria a interface gráfica usando tkinter."""
    root = tk.Tk()
    root.title("Transcrição de Vídeo")
    root.geometry("600x450")  # Aumentei a altura para acomodar o novo campo

    # Frame principal
    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Entrada do caminho do vídeo ou URL
    ttk.Label(main_frame, text="Caminho do Vídeo ou URL do YouTube:").grid(row=0, column=0, sticky=tk.W, pady=5)
    entry_path = ttk.Entry(main_frame, width=50)
    entry_path.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
    ttk.Button(main_frame, text="Selecionar Arquivo", command=lambda: browse_file(entry_path)).grid(row=1, column=1, padx=5)

    # Entrada do caminho do arquivo de saída
    ttk.Label(main_frame, text="Arquivo de Saída (SRT):").grid(row=2, column=0, sticky=tk.W, pady=5)
    output_entry = ttk.Entry(main_frame, width=50)
    output_entry.insert(0, "transcription.srt")
    output_entry.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

    # Entrada do prompt inicial (opcional)
    ttk.Label(main_frame, text="Prompt Inicial (opcional):").grid(row=4, column=0, sticky=tk.W, pady=5)
    prompt_entry = ttk.Entry(main_frame, width=50)
    prompt_entry.insert(0, "")  # Campo vazio por padrão
    prompt_entry.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)

    # Seleção de idioma
    ttk.Label(main_frame, text="Idioma:").grid(row=6, column=0, sticky=tk.W, pady=5)
    language_var = tk.StringVar(value="pt")
    language_menu = ttk.Combobox(main_frame, textvariable=language_var, values=["pt", "en", "es"], state="readonly")
    language_menu.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=5)

    # Seleção do tamanho do modelo
    ttk.Label(main_frame, text="Tamanho do Modelo:").grid(row=8, column=0, sticky=tk.W, pady=5)
    model_var = tk.StringVar(value="medium")
    model_menu = ttk.Combobox(main_frame, textvariable=model_var, values=["tiny", "base", "small", "medium", "large", "large-v3-turbo"], state="readonly")
    model_menu.grid(row=9, column=0, sticky=(tk.W, tk.E), pady=5)

    # Botão de transcrição
    transcribe_button = ttk.Button(main_frame, text="Iniciar Transcrição", 
                                   command=lambda: start_transcription(entry_path, output_entry, language_var, model_var, prompt_entry, status_label))
    transcribe_button.grid(row=10, column=0, columnspan=2, pady=10)

    # Label de status
    status_label = ttk.Label(main_frame, text="Aguardando ação...", wraplength=500)
    status_label.grid(row=11, column=0, columnspan=2, pady=10)

    # Configura o redimensionamento
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    main_frame.columnconfigure(0, weight=1)

    root.mainloop()

if __name__ == "__main__":
    create_gui()