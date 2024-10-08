from diffusers import DiffusionPipeline, AutoencoderKL, StableDiffusionXLControlNetPipeline, ControlNetModel, StableDiffusionXLPipeline, StableDiffusionXLInpaintPipeline
from diffusers.utils import load_image
from diffusers.pipelines.stable_diffusion_xl.pipeline_output import StableDiffusionXLPipelineOutput
import torch
from diffusers.schedulers import DPMSolverMultistepScheduler, LCMScheduler, EulerAncestralDiscreteScheduler
from controlnet_aux.processor import Processor

import os
import configparser
# ファイルの存在チェック用モジュール
import errno
import cv2
from PIL import Image
import time
import numpy as np
import GPUtil
import gc

class SDXLCconfig:
    def __init__(self, config_ini_path = './configs/config.ini'):
        # iniファイルの読み込み
        self.config_ini = configparser.ConfigParser()

        # 指定したiniファイルが存在しない場合、エラー発生
        if not os.path.exists(config_ini_path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), config_ini_path)

        self.config_ini.read(config_ini_path, encoding='utf-8')
        SDXLC_items = self.config_ini.items('SDXLC')
        self.SDXLC_config_dict = dict(SDXLC_items)

class SDXLC:
    def __init__(self,device = None, config_ini_path = './configs/config.ini'):

        SDXLC_config = SDXLCconfig(config_ini_path = config_ini_path)
        config_dict = SDXLC_config.SDXLC_config_dict


        if device is not None:
            self.device = device
        else:
            device = config_dict["device"]

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            if device != "auto":
                self.device = device

        self.last_latents = None
        self.last_step = -1
        self.last_timestep = 1000

        self.n_steps = int(config_dict["n_steps"])
        if not config_dict["high_noise_frac"] == "None":
          self.high_noise_frac = float(config_dict["high_noise_frac"])
        else:
          self.high_noise_frac = None
        self.seed = int(config_dict["seed"])
        self.generator = torch.Generator(device=self.device).manual_seed(self.seed)

        self.controlnet_path = config_dict.get("controlnet_path", "None")
        self.controlnet_path_s = config_dict.get("controlnet_path_s", "None")
        #self.controlnet_path_i = config_dict.get("controlnet_path_i", "None")

        self.control_mode = config_dict["control_mode"]
        if self.control_mode == "None":
            self.control_mode = None

        self.vae_model_path = config_dict["vae_model_path"]
        self.VAE_FLAG = True
        if self.vae_model_path == "None":
            self.vae_model_path = None
            self.VAE_FLAG = False
            
        self.controlnet_s_single_path = config_dict.get("controlnet_s_single_path", None)
        #self.controlnet_i_single_path = config_dict.get("controlnet_i_single_path", None)

        self.from_single_file = config_dict.get("from_single_file", "None")
        self.SINGLE_FILE_FLAG = True
        if self.from_single_file != "True":
            self.from_single_file = None
            self.SINGLE_FILE_FLAG = False
            

        self.base_model_path = config_dict["base_model_path"]

        self.REFINER_FLAG = True
        self.refiner_model_path = config_dict["refiner_model_path"]
        if self.refiner_model_path == "None":
            self.refiner_model_path = None
            self.REFINER_FLAG = False


        self.LORA_FLAG = True
        self.trigger_word = config_dict.get("trigger_word", None)
        self.lora_weight_path = config_dict.get("lora_weight_path", None)
        self.lora_scale = config_dict.get("lora_scale", None)
        if (self.lora_weight_path == "None") or (self.lora_weight_path is None):
          self.lora_weight_path = None
          self.LORA_FLAG = False
          self.trigger_word  = None
          self.lora_scale = None
        else:
            if self.lora_scale is None:
                self.lora_scale = 1.0
            else:
                self.lora_scale = float(self.lora_scale)

        

        self.LORA_FLAG2 = True
        self.trigger_word2 = config_dict.get("trigger_word2", None)
        self.lora_weight_path2 = config_dict.get("lora_weight_path2", None)
        self.lora_scale2 = config_dict.get("lora_scale2", None)
        if (self.lora_weight_path2 == "None") or (self.lora_weight_path2 is None):
            self.lora_weight_path2 = None
            self.LORA_FLAG2 = False
            self.trigger_word2  = None
            self.lora_scale2 = None
        else:
            if self.lora_scale2 is None:
                self.lora_scale2 = 1.0
            else:
                self.lora_scale2 = float(self.lora_scale2)
        
        self.select_solver = config_dict.get("select_solver", "DPM")

        self.use_karras_sigmas = config_dict["use_karras_sigmas"]
        if self.use_karras_sigmas == "True":
            self.use_karras_sigmas = True
        else:
            self.use_karras_sigmas = False
        self.scheduler_algorithm_type = config_dict["scheduler_algorithm_type"]
        if config_dict["solver_order"] != "None":
            self.solver_order = int(config_dict["solver_order"])
        else:
            self.solver_order = None

        self.cfg_scale = float(config_dict["cfg_scale"])
        self.width = int(config_dict["width"])
        self.height = int(config_dict["height"])
        self.output_type = config_dict["output_type"]
        self.aesthetic_score = float(config_dict["aesthetic_score"])
        self.negative_aesthetic_score = float(config_dict["negative_aesthetic_score"])

        self.save_latent_simple = config_dict["save_latent_simple"]
        if self.save_latent_simple == "True":
            self.save_latent_simple = True
            print("use vallback save_latent_simple")
        else:
            self.save_latent_simple = False

        self.save_latent_overstep = config_dict["save_latent_overstep"]
        if self.save_latent_overstep == "True":
            self.save_latent_overstep = True
            print("use vallback save_latent_overstep")
        else:
            self.save_latent_overstep = False

        self.save_latent_approximation = config_dict["save_latent_approximation"]
        if self.save_latent_approximation == "True":
            self.save_latent_approximation = True
            print("use vallback save_latent_approximation")
        else:
            self.save_latent_approximation = False

        self.use_callback = False
        if self.save_latent_simple or self.save_latent_overstep or self.save_latent_approximation:
            self.use_callback = True

        if self.save_latent_simple and self.save_latent_overstep:
            raise ValueError("save_latent_simple and save_latent_overstep cannot be set at the same time")

        self.base_s, self.base_i , self.refiner = self.preprepare_model()


    def preprepare_model(self, controlnet_path = None):
        if controlnet_path is not None:
            self.controlnet_path = controlnet_path

        use_single_s = False
        if self.controlnet_s_single_path is not None:
            use_single_s = True
        
        if not use_single_s:
            controlnet_s = ControlNetModel.from_pretrained(
                    self.controlnet_path_s,
                    use_safetensors=True,
                    torch_dtype=torch.float16)
        else:
            controlnet_s = ControlNetModel.from_single_file(
                    self.controlnet_s_single_path,
                    use_safetensors=True,
                    torch_dtype=torch.float16)
        
        if self.VAE_FLAG:
            vae = AutoencoderKL.from_pretrained(
                self.vae_model_path,
                torch_dtype=torch.float16)
            
            if not self.SINGLE_FILE_FLAG:
                base_s = StableDiffusionXLControlNetPipeline.from_pretrained(
                    self.base_model_path,
                    controlnet=controlnet_s,
                    vae=vae,
                    torch_dtype=torch.float16,
                    variant="fp16",
                    use_safetensors=True
                )
                base_i = StableDiffusionXLInpaintPipeline.from_pretrained(
                    self.base_model_path,
                    vae=vae,
                    torch_dtype=torch.float16,
                    variant="fp16",
                    use_safetensors=True
                )
            else:
                pipe = StableDiffusionXLPipeline.from_single_file(
                    self.base_model_path,
                    extract_ema=True,
                    torch_dtype=torch.float16 
                    )
                base_s = StableDiffusionXLControlNetPipeline(controlnet = controlnet_s, **pipe.components)
                base_i = StableDiffusionXLInpaintPipeline(**pipe.components)
            #base_s.to(self.device)
            #base_i.to(self.device)
            base_s.enable_model_cpu_offload()
            base_i.enable_model_cpu_offload()

            if self.REFINER_FLAG:
                refiner = DiffusionPipeline.from_pretrained(
                    self.refiner_model_path,
                    text_encoder_2=base_s.text_encoder_2,
                    vae=vae,
                    requires_aesthetics_score=True,
                    torch_dtype=torch.float16,
                    variant="fp16",
                    use_safetensors=True
                )

                refiner.enable_model_cpu_offload()
            else:
                refiner = None

        else:
            if not self.SINGLE_FILE_FLAG:
                base_s = StableDiffusionXLControlNetPipeline.from_pretrained(
                    self.base_model_path,
                    controlnet=controlnet_s,
                    torch_dtype=torch.float16,
                    variant="fp16",
                    use_safetensors=True
                )
                base_i = StableDiffusionXLInpaintPipeline.from_pretrained(
                    self.base_model_path,
                    torch_dtype=torch.float16,
                    variant="fp16",
                    use_safetensors=True
                )
            else:
                pipe = StableDiffusionXLPipeline.from_single_file(
                    self.base_model_path,
                    extract_ema=True,
                    torch_dtype=torch.float16 
                    )
                base_s = StableDiffusionXLControlNetPipeline(controlnet = controlnet_s, **pipe.components)
                base_i = StableDiffusionXLInpaintPipeline(**pipe.components)
            #base_s.to(self.device, torch.float16)
            #base_i.to(self.device, torch.float16)
            base_s.enable_model_cpu_offload()
            base_i.enable_model_cpu_offload()

            if self.REFINER_FLAG:
                refiner = DiffusionPipeline.from_pretrained(
                    self.refiner_model_path,
                    text_encoder_2=base_s.text_encoder_2,
                    requires_aesthetics_score=True,
                    torch_dtype=torch.float16,
                    variant="fp16",
                    use_safetensors=True
                )

                refiner.enable_model_cpu_offload()
            else:
                refiner = None

        if self.LORA_FLAG:
            base_s.load_lora_weights(self.lora_weight_path, adapter_name="lora1")
            base_i.load_lora_weights(self.lora_weight_path, adapter_name="lora1")
            if self.LORA_FLAG2:
                base_s.load_lora_weights(self.lora_weight_path2, adapter_name="lora2")
                base_i.load_lora_weights(self.lora_weight_path2, adapter_name="lora2")
                base_s.set_adapters(["lora1", "lora2"], adapter_weights=[1.0, 1.0])
                base_i.set_adapters(["lora1", "lora2"], adapter_weights=[1.0, 1.0])
        
        if self.select_solver == "DPM":
            if self.solver_order is not None:
                base_s.scheduler = DPMSolverMultistepScheduler.from_config(
                        base_s.scheduler.config,
                        use_karras_sigmas=self.use_karras_sigmas,
                        Algorithm_type =self.scheduler_algorithm_type,
                        solver_order=self.solver_order,
                        )
                base_i.scheduler = DPMSolverMultistepScheduler.from_config(
                        base_i.scheduler.config,
                        use_karras_sigmas=self.use_karras_sigmas,
                        Algorithm_type =self.scheduler_algorithm_type,
                        solver_order=self.solver_order,
                        )

            else:
                base_s.scheduler = DPMSolverMultistepScheduler.from_config(
                        base_s.scheduler.config,
                        use_karras_sigmas=self.use_karras_sigmas,
                        Algorithm_type =self.scheduler_algorithm_type,
                        )
                base_i.scheduler = DPMSolverMultistepScheduler.from_config(
                        base_i.scheduler.config,
                        use_karras_sigmas=self.use_karras_sigmas,
                        Algorithm_type =self.scheduler_algorithm_type,
                        )
        elif self.select_solver == "LCM":
            base_s.scheduler = LCMScheduler.from_config(base_s.scheduler.config)
            base_i.scheduler = LCMScheduler.from_config(base_i.scheduler.config)
        elif self.select_solver == "Eulera":
            base_s.scheduler = EulerAncestralDiscreteScheduler.from_config(base_s.scheduler.config)
            base_i.scheduler = EulerAncestralDiscreteScheduler.from_config(base_i.scheduler.config)
        else:
            raise ValueError("select_solver is only 'DPM' or 'LCM' or 'Eulera'.")
            
        return base_s,base_i, refiner
    
    def memory_reset_model(self, controlnet_path = None):
        GPUtil.showUtilization()
        del self.base
        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.empty_cache()
        GPUtil.showUtilization()
        self.base , self.refiner = self.preprepare_model(controlnet_path = controlnet_path)


    def prepare_referimage(self,input_refer_image_path,output_refer_image_path, low_threshold = 100, high_threshold = 200):

        mode = None
        if self.control_mode is not None:
            mode = self.control_mode
        else:
            raise ValueError("control_mode is not set")

        def prepare_openpose(input_refer_image_path,output_refer_image_path, mode):

            # 初期画像の準備
            init_image = load_image(input_refer_image_path)
            init_image = init_image.resize((self.width, self.height))

            processor = Processor(mode)
            processed_image = processor(init_image, to_pil=True)

            processed_image.save(output_refer_image_path)




        def prepare_canny(input_refer_image_path,output_refer_image_path, low_threshold = 100, high_threshold = 200):
            init_image = load_image(input_refer_image_path)
            init_image = init_image.resize((self.width, self.height))

            # コントロールイメージを作成するメソッド
            def make_canny_condition(image, low_threshold = 100, high_threshold = 200):
                image = np.array(image)
                image = cv2.Canny(image, low_threshold, high_threshold)
                image = image[:, :, None]
                image = np.concatenate([image, image, image], axis=2)
                return Image.fromarray(image)

            control_image = make_canny_condition(init_image, low_threshold, high_threshold)
            control_image.save(output_refer_image_path)

        def prepare_depthmap(input_refer_image_path,output_refer_image_path):

            # 初期画像の準備
            init_image = load_image(input_refer_image_path)
            init_image = init_image.resize((self.width, self.height))
            processor = Processor("depth_midas")
            depth_image = processor(init_image, to_pil=True)
            depth_image.save(output_refer_image_path)

        def prepare_zoe_depthmap(input_refer_image_path,output_refer_image_path):

            torch.hub.help(
                "intel-isl/MiDaS",
                "DPT_BEiT_L_384",
                force_reload=True
                )
            model_zoe_n = torch.hub.load(
                "isl-org/ZoeDepth",
                "ZoeD_NK",
                pretrained=True
                ).to("cuda")

            init_image = load_image(input_refer_image_path)
            init_image = init_image.resize((self.width, self.height))

            depth_numpy = model_zoe_n.infer_pil(init_image)  # return: numpy.ndarray

            from zoedepth.utils.misc import colorize
            colored = colorize(depth_numpy) # numpy.ndarray => numpy.ndarray

            # gamma correction
            img = colored / 255
            img = np.power(img, 2.2)
            img = (img * 255).astype(np.uint8)

            Image.fromarray(img).save(output_refer_image_path)


        if "openpose" in mode:
            prepare_openpose(input_refer_image_path,output_refer_image_path, mode)
        elif mode == "canny":
            prepare_canny(input_refer_image_path,output_refer_image_path, low_threshold = low_threshold, high_threshold = high_threshold)
        elif mode == "depth":
            prepare_depthmap(input_refer_image_path,output_refer_image_path)
        elif mode == "zoe_depth":
            prepare_zoe_depthmap(input_refer_image_path,output_refer_image_path)
        elif mode == "tile" or mode == "scribble":
            init_image = load_image(input_refer_image_path)
            init_image.save(output_refer_image_path)
        else:
            raise ValueError("control_mode is not set")


    def generate_image(self, prompt, neg_prompt, image_path, seed = None, controlnet_conditioning_scale = 1.0, mode = "scribble", mask_image = None):
        def decode_tensors(pipe, step, timestep, callback_kwargs):
            if self.save_latent_simple:
                callback_kwargs = decode_tensors_simple(pipe, step, timestep, callback_kwargs)
            elif self.save_latent_overstep:
                callback_kwargs = decode_tensors_residual(pipe, step, timestep, callback_kwargs)
            else:
                raise ValueError("save_latent_simple or save_latent_overstep must be set or 'save_latent_approximation = False'")
            return callback_kwargs


        def decode_tensors_simple(pipe, step, timestep, callback_kwargs):
            latents = callback_kwargs["latents"]
            imege = None
            if self.save_latent_simple and not self.save_latent_approximation:
                image = latents_to_rgb_vae(latents,pipe)
            elif self.save_latent_approximation:
                image = latents_to_rgb_approximation(latents,pipe)
            else:
                raise ValueError("save_latent_simple or save_latent_approximation is not set")
            gettime = time.time()
            formatted_time_human_readable = time.strftime("%Y%m%d_%H%M%S", time.localtime(gettime))
            image.save(f"./outputs/latent_{formatted_time_human_readable}_{step}_{timestep}.png")

            return callback_kwargs

        def decode_tensors_residual(pipe, step, timestep, callback_kwargs):
            latents = callback_kwargs["latents"]
            if step > 0:
                residual = latents - self.last_latents
                goal = self.last_latents + residual * ((self.last_timestep) / (self.last_timestep - timestep))
                #print( ((self.last_timestep) / (self.last_timestep - timestep)))
            else:
                goal = latents

            if self.save_latent_overstep and not self.save_latent_approximation:
                image = latents_to_rgb_vae(goal,pipe)
            elif self.save_latent_approximation:
                image = latents_to_rgb_approximation(goal,pipe)
            else:
                raise ValueError("save_latent_simple or save_latent_approximation is not set")

            gettime = time.time()
            formatted_time_human_readable = time.strftime("%Y%m%d_%H%M%S", time.localtime(gettime))
            image.save(f"./outputs/latent_{formatted_time_human_readable}_{step}_{timestep}.png")

            self.last_latents = latents
            self.last_step = step
            self.last_timestep = timestep

            if timestep == 0:
                self.last_latents = None
                self.last_step = -1
                self.last_timestep = 100

            return callback_kwargs

        def latents_to_rgb_vae(latents,pipe):

            pipe.upcast_vae()
            latents = latents.to(next(iter(pipe.vae.post_quant_conv.parameters())).dtype)
            images = pipe.vae.decode(latents / pipe.vae.config.scaling_factor, return_dict=False)[0]
            images = pipe.image_processor.postprocess(images, output_type='pil')
            pipe.vae.to(dtype=torch.float16)

            return StableDiffusionXLPipelineOutput(images=images).images[0]

        def latents_to_rgb_approximation(latents, pipe):
            weights = (
                (60, -60, 25, -70),
                (60,  -5, 15, -50),
                (60,  10, -5, -35)
            )

            weights_tensor = torch.t(torch.tensor(weights, dtype=latents.dtype).to(latents.device))
            biases_tensor = torch.tensor((150, 140, 130), dtype=latents.dtype).to(latents.device)
            rgb_tensor = torch.einsum("...lxy,lr -> ...rxy", latents, weights_tensor) + biases_tensor.unsqueeze(-1).unsqueeze(-1)
            image_array = rgb_tensor.clamp(0, 255)[0].byte().cpu().numpy()
            image_array = image_array.transpose(1, 2, 0)  # Change the order of dimensions

            return Image.fromarray(image_array)
        
        def load_image_path(image_path):
            # もし image_path が str ならファイルパスとして画像を読み込む
            if isinstance(image_path, str):
                image = load_image(image_path)
                print("Image loaded from file path.")
            # もし image_path が PIL イメージならそのまま使用
            elif isinstance(image_path, Image.Image):
                image = image_path
                print("PIL Image object provided.")
            # もし image_path が Torch テンソルならそのまま使用
            elif isinstance(image_path, torch.Tensor):
                image = image_path.unsqueeze(0)
                image = image.permute(0, 3, 1, 2)
                image = image/255.0
                print("Torch Tensor object provided.")
            else:
                raise TypeError("Unsupported type. Provide a file path, PIL Image, or Torch Tensor.")
            
            return image

        if seed is not None:
            self.generator = torch.Generator(device=self.device).manual_seed(seed)

        control_image = load_image_path(image_path)
        if mask_image is not None:
            mask_image = load_image_path(mask_image)
        
        print("control_image")

        if mode == "scribble":
            print("scribble")
            self.base = self.base_s
        elif mode == "inpaint":
            print("inpaint")
            self.base = self.base_i
            self.cfg_scale = 1.0

        if (self.trigger_word is not None) and (self.trigger_word != "None"):
            prompt = prompt + ", " + self.trigger_word
            print(self.trigger_word)
        if (self.trigger_word2 is not None) and (self.trigger_word2 != "None"):
            prompt = prompt + ", " + self.trigger_word2
            print(self.trigger_word2)

        image = None
        if self.use_callback:
            if self.LORA_FLAG:
                if self.REFINER_FLAG:
                    image = self.base(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        image=control_image,
                        mask_image = mask_image,
                        guidance_scale=self.cfg_scale,
                        controlnet_conditioning_scale=controlnet_conditioning_scale,
                        num_inference_steps=self.n_steps,
                        denoising_end=self.high_noise_frac,
                        output_type="latent",
                        width = self.width,
                        height = self.height,
                        generator=self.generator,
                        cross_attention_kwargs={"scale": self.lora_scale},
                        callback_on_step_end=decode_tensors,
                        callback_on_step_end_tensor_inputs=["latents"],
                        ).images[0]
                    image = self.refiner(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        guidance_scale=self.cfg_scale,
                        aesthetic_score = self.aesthetic_score,
                        negative_aesthetic_score = self.negative_aesthetic_score,
                        num_inference_steps=self.n_steps,
                        denoising_start=self.high_noise_frac,
                        callback_on_step_end=decode_tensors,
                        callback_on_step_end_tensor_inputs=["latents"],
                        image=image[None, :]
                        ).images[0]
                #refiner を利用しない場合
                else:
                    image = self.base(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        image=control_image,
                        mask_image = mask_image,
                        guidance_scale=self.cfg_scale,
                        controlnet_conditioning_scale=controlnet_conditioning_scale,
                        num_inference_steps=self.n_steps,
                        denoising_end=self.high_noise_frac,
                        output_type=self.output_type,
                        width = self.width,
                        height = self.height,
                        generator=self.generator,
                        callback_on_step_end=decode_tensors,
                        callback_on_step_end_tensor_inputs=["latents"],
                        cross_attention_kwargs={"scale": self.lora_scale},
                        ).images[0]
            #LORAを利用しない場合
            else:
                if self.REFINER_FLAG:
                    image = self.base(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        image=control_image,
                        mask_image = mask_image,
                        guidance_scale=self.cfg_scale,
                        controlnet_conditioning_scale=controlnet_conditioning_scale,
                        num_inference_steps=self.n_steps,
                        denoising_end=self.high_noise_frac,
                        output_type="latent",
                        width = self.width,
                        height = self.height,
                        callback_on_step_end=decode_tensors,
                        callback_on_step_end_tensor_inputs=["latents"],
                        generator=self.generator
                        ).images[0]
                    image = self.refiner(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        guidance_scale=self.cfg_scale,
                        aesthetic_score = self.aesthetic_score,
                        negative_aesthetic_score = self.negative_aesthetic_score,
                        num_inference_steps=self.n_steps,
                        denoising_start=self.high_noise_frac,
                        callback_on_step_end=decode_tensors,
                        callback_on_step_end_tensor_inputs=["latents"],
                        image=image[None, :]
                        ).images[0]
                #refiner を利用しない場合
                else:
                    image = self.base(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        image=control_image,
                        mask_image = mask_image,
                        guidance_scale=self.cfg_scale,
                        controlnet_conditioning_scale=controlnet_conditioning_scale,
                        num_inference_steps=self.n_steps,
                        denoising_end=self.high_noise_frac,
                        output_type=self.output_type,
                        width = self.width,
                        height = self.height,
                        callback_on_step_end=decode_tensors,
                        callback_on_step_end_tensor_inputs=["latents"],
                        generator=self.generator
                        ).images[0]
        #latentを保存しない場合
        else:
            if self.LORA_FLAG:
                if self.REFINER_FLAG:
                    image = self.base(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        image=control_image,
                        mask_image = mask_image,
                        guidance_scale=self.cfg_scale,
                        controlnet_conditioning_scale=controlnet_conditioning_scale,
                        num_inference_steps=self.n_steps,
                        denoising_end=self.high_noise_frac,
                        output_type="latent",
                        width = self.width,
                        height = self.height,
                        generator=self.generator,
                        cross_attention_kwargs={"scale": self.lora_scale},
                        ).images[0]
                    image = self.refiner(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        guidance_scale=self.cfg_scale,
                        aesthetic_score = self.aesthetic_score,
                        negative_aesthetic_score = self.negative_aesthetic_score,
                        num_inference_steps=self.n_steps,
                        denoising_start=self.high_noise_frac,
                        image=image[None, :]
                        ).images[0]
                # refiner を利用しない場合
                else:
                    image = self.base(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        image=control_image,
                        mask_image = mask_image,
                        guidance_scale=self.cfg_scale,
                        controlnet_conditioning_scale=controlnet_conditioning_scale,
                        num_inference_steps=self.n_steps,
                        denoising_end=self.high_noise_frac,
                        output_type=self.output_type,
                        width = self.width,
                        height = self.height,
                        generator=self.generator,
                        cross_attention_kwargs={"scale": self.lora_scale},
                        ).images[0]

            # LORAを利用しない場合
            else:
                if self.REFINER_FLAG:
                    image = self.base(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        image=control_image,
                        mask_image = mask_image,
                        guidance_scale=self.cfg_scale,
                        controlnet_conditioning_scale=controlnet_conditioning_scale,
                        num_inference_steps=self.n_steps,
                        denoising_end=self.high_noise_frac,
                        output_type="latent",
                        width = self.width,
                        height = self.height,
                        generator=self.generator
                        ).images[0]
                    image = self.refiner(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        guidance_scale=self.cfg_scale,
                        aesthetic_score = self.aesthetic_score,
                        negative_aesthetic_score = self.negative_aesthetic_score,
                        num_inference_steps=self.n_steps,
                        denoising_start=self.high_noise_frac,
                        image=image[None, :]
                        ).images[0]
                # refiner を利用しない場合
                else:
                    image = self.base(
                        prompt=prompt,
                        negative_prompt=neg_prompt,
                        image=control_image,
                        mask_image = mask_image,
                        guidance_scale=self.cfg_scale,
                        controlnet_conditioning_scale=controlnet_conditioning_scale,
                        num_inference_steps=self.n_steps,
                        denoising_end=self.high_noise_frac,
                        output_type=self.output_type,
                        width = self.width,
                        height = self.height,
                        generator=self.generator
                        ).images[0]

        return image
