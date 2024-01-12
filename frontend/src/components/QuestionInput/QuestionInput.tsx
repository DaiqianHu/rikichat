import { useState } from "react";
import React, { useRef } from 'react';
import { Stack, TextField } from "@fluentui/react";
import { SendRegular } from "@fluentui/react-icons";
import Send from "../../assets/Send.svg";
import FileUpload from "../../assets/FileUpload.svg";
import Microphone from "../../assets/Microphone.svg";
import MicroPhoneRecording from "../../assets/MicrophoneRecording.svg";
import styles from "./QuestionInput.module.css";

interface Props {
    onSend: (question: string, imageUrl: string, id?: string) => void;
    disabled: boolean;
    placeholder?: string;
    clearOnSend?: boolean;
    conversationId?: string;
}

export const QuestionInput = ({ onSend, disabled, placeholder, clearOnSend, conversationId }: Props) => {
    const [question, setQuestion] = useState<string>("");
    const [file, setFile] = useState<File | null>(null);
    const [imageUrl, setImageUrl] = useState<string | "">("");
    const [recording, setRecording] = useState(false);
    const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
    const [speechToTexting, setSpeechToTexting] = useState<"converting" | "success" | "failure">("converting");

    const sendQuestion = () => {
        if (disabled || !question.trim()) {
            return;
        }

        if(conversationId){
            onSend(question, imageUrl, conversationId);
        }else{
            onSend(question, imageUrl);
        }

        if (clearOnSend) {
            setQuestion("");
            setFile(null);
            setImageUrl("");
        }
    };

    const onEnterPress = (ev: React.KeyboardEvent<Element>) => {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            sendQuestion();
        }
    };

    const onQuestionChange = (_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setQuestion(newValue || "");
    };

    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileUploadClick = () => {
        if (fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files.length > 0) {
            const file = event.target.files[0];
            console.log(file);

            // handle the file here
            setFile(file);
            const reader = new FileReader();
            reader.onloadend = () => {
                setImageUrl(reader.result as string); // reader.result contains the base64 string
            };
            reader.readAsDataURL(file);
        }
    };

    const handleAudioRecordingClick = () => {
        if (recording) {
        // Stop recording
        mediaRecorder?.stop();
        setRecording(false);
        } else {
        // Start recording
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                const newMediaRecorder = new MediaRecorder(stream);
                const audioChunks: BlobPart[] = [];

                newMediaRecorder.ondataavailable = event => {
                    // Collect audio data chunks while recording
                    audioChunks.push(event.data);
                };

                newMediaRecorder.onstop = () => {
                    setSpeechToTexting("converting");

                    // Create a Blob object from the audio data chunks when recording stops
                    const audioData = new Blob(audioChunks, { type: 'audio/wav' });

                    // Create a FormData object so we can send this audio data to our server
                    const formData = new FormData();
                    formData.append("audio", audioData);

                    // Send the audio data to our backend
                    fetch("/speech_to_text", {
                        method: "POST",
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        // The response from the server contains the text of audio file
                        setSpeechToTexting("success");

                        console.log(data);
                        setQuestion(data.text);
                    })
                    .catch(error => {
                        console.error(error);
                        setSpeechToTexting("failure");
                    });
                };
                newMediaRecorder.start();
                setMediaRecorder(newMediaRecorder);
                setRecording(true);
            });
        }
    };

    const sendQuestionDisabled = disabled || !question.trim();

    return (
        <Stack horizontal className={styles.questionInputContainer}>
            <TextField
                className={styles.questionInputTextArea}
                placeholder={placeholder}
                multiline
                resizable={false}
                borderless
                value={question}
                onChange={onQuestionChange}
                onKeyDown={onEnterPress}
            />
            <img src={imageUrl}/>
            <div className={styles.questionMicrophoneButtonContainer} 
                role="button" 
                tabIndex={2}
                aria-label="Microphone button"
                onClick={handleAudioRecordingClick}
            >
                { recording ? 
                    <img src={MicroPhoneRecording} className={styles.questionMicrophoneButton}/>
                    :
                    <img src={Microphone} className={styles.questionMicrophoneButton}/>
                }
            </div>
            <div className={styles.questionFileUploadButtonContainer} 
                role="button" 
                tabIndex={1}
                aria-label="File Upload button"
                onClick={handleFileUploadClick}
            >
            <img src={FileUpload} className={styles.questionFileUploadButton}/>
            </div>
            <input type="file" ref={fileInputRef} onChange={handleFileUpload} accept="image/*" style={{ display: 'none' }} />
            <div className={styles.questionInputSendButtonContainer} 
                role="button" 
                tabIndex={0}
                aria-label="Ask question button"
                onClick={sendQuestion}
                onKeyDown={e => e.key === "Enter" || e.key === " " ? sendQuestion() : null}
            >
                { sendQuestionDisabled ? 
                    <SendRegular className={styles.questionInputSendButtonDisabled}/>
                    :
                    <img src={Send} className={styles.questionInputSendButton}/>
                }
            </div>
            <div className={styles.questionInputBottomBorder} />
        </Stack>
    );
};
