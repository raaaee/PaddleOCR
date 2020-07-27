package com.baidu.paddle.lite.demo.ocr;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Message;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import java.io.IOException;
import java.io.InputStream;

public class MiniActivity extends AppCompatActivity {


    public static final int REQUEST_LOAD_MODEL = 0;
    public static final int REQUEST_RUN_MODEL = 1;
    public static final int REQUEST_UNLOAD_MODEL = 2;
    public static final int RESPONSE_LOAD_MODEL_SUCCESSED = 0;
    public static final int RESPONSE_LOAD_MODEL_FAILED = 1;
    public static final int RESPONSE_RUN_MODEL_SUCCESSED = 2;
    public static final int RESPONSE_RUN_MODEL_FAILED = 3;

    private static final String TAG = "MiniActivity";

    protected Handler receiver = null; // Receive messages from worker thread
    protected Handler sender = null; // Send command to worker thread
    protected HandlerThread worker = null; // Worker thread to load&run model
    protected volatile Predictor predictor = null;

    private String assetModelDirPath = "models/ocr_v1_for_cpu";
    private String assetlabelFilePath = "labels/ppocr_keys_v1.txt";

    private Button button;
    private ImageView imageView; // 显示图像
    private TextView textView; // 显示结果

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_mini);

        Log.i(TAG, "SHOW in Logcat");

        // Prepare the worker thread for mode loading and inference
        worker = new HandlerThread("Predictor Worker");
        worker.start();
        sender = new Handler(worker.getLooper()) {
            public void handleMessage(Message msg) {
                switch (msg.what) {
                    case REQUEST_LOAD_MODEL:
                        // Load model and reload test image
                        if (!onLoadModel()) {
                            runOnUiThread(new Runnable() {
                                @Override
                                public void run() {
                                    Toast.makeText(MiniActivity.this, "Load model failed!", Toast.LENGTH_SHORT).show();
                                }
                            });
                        }
                        break;
                    case REQUEST_RUN_MODEL:
                        // Run model if model is loaded
                        final boolean isSuccessed = onRunModel();
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                if (isSuccessed){
                                    onRunModelSuccessed();
                                }else{
                                    Toast.makeText(MiniActivity.this, "Run model failed!", Toast.LENGTH_SHORT).show();
                                }
                            }
                        });
                        break;
                }
            }
        };
        sender.sendEmptyMessage(REQUEST_LOAD_MODEL); // 对应上面的REQUEST_LOAD_MODEL， 调用onLoadModel()

        imageView = findViewById(R.id.imageView);
        textView = findViewById(R.id.sample_text);
        button = findViewById(R.id.button);
        button.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sender.sendEmptyMessage(REQUEST_RUN_MODEL);
            }
        });


    }

    @Override
    protected void onDestroy() {
        onUnloadModel();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR2) {
            worker.quitSafely();
        } else {
            worker.quit();
        }
        super.onDestroy();
    }

    /**
     * onCreate的时候调用， 模型初始化
     *
     * @return
     */
    private boolean onLoadModel() {
        if (predictor == null) {
            predictor = new Predictor();
        }
        return predictor.init(this, assetModelDirPath, assetlabelFilePath);
    }

    /**
     * on
     *
     * @return
     */
    private boolean onRunModel() {
        try {
            String assetImagePath = "images/5.jpg";
            InputStream imageStream = getAssets().open(assetImagePath);
            Bitmap image = BitmapFactory.decodeStream(imageStream);
            // 这里输入是Bitmap
            predictor.setInputImage(image);
            return predictor.isLoaded() && predictor.runModel();
        } catch (IOException e) {
            e.printStackTrace();
            return false;
        }
    }

    private void onRunModelSuccessed() {
        Log.i(TAG, "onRunModelSuccessed");
        textView.setText(predictor.outputResult);
        imageView.setImageBitmap(predictor.outputImage);
    }

    private void onUnloadModel() {
        if (predictor != null) {
            predictor.releaseModel();
        }
    }
}
