from psd_tools import PSDImage
from PIL import Image
import os

class ImageProcessor:
    def __init__(self):
        # 创建输出文件夹
        self.png_folder = 'png_output'
        self.final_folder = 'final_output'
        os.makedirs(self.png_folder, exist_ok=True)
        os.makedirs(self.final_folder, exist_ok=True)

    def validate_template(self, template_path):
        """验证模板图片是否有透明通道"""
        try:
            with Image.open(template_path) as template:
                if template.mode != 'RGBA':
                    raise ValueError("模板必须是带透明通道的PNG图片(RGBA格式)")
                return True
        except Exception as e:
            print(f"模板验证失败: {str(e)}")
            return False

    def remove_white_background(self, image):
        """去除图片中的白色背景"""
        # 确保图片在RGBA模式
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # 获取图片数据
        data = image.getdata()
        
        # 创建新的像素数据，将白色背景转为透明
        new_data = []
        for item in data:
            # 检查像素是否接近白色（考虑到可能的轻微色差）
            if item[0] > 250 and item[1] > 250 and item[2] > 250:
                # 完全透明
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        
        # 更新图片数据
        image.putdata(new_data)
        return image

    def convert_psd_to_png(self, psd_path):
        """将PSD文件转换为PNG"""
        if not os.path.exists(psd_path):
            raise FileNotFoundError(f"找不到PSD文件: {psd_path}")
            
        try:
            # 打开PSD文件
            psd = PSDImage.open(psd_path)
            
            # 合并所有图层并确保使用RGBA模式
            image = psd.composite()
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # 去除白色背景
            image = self.remove_white_background(image)
            
            # 生成输出文件名
            filename = os.path.basename(psd_path)
            png_name = os.path.splitext(filename)[0] + '.png'
            output_path = os.path.join(self.png_folder, png_name)
            
            # 保存为PNG，确保保留透明通道
            image.save(output_path, 'PNG', optimize=False)
            print(f"已转换: {psd_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            import traceback
            print(f"\n处理 {psd_path} 时出错:")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print("详细错误信息:")
            print(traceback.format_exc())
            raise

    def apply_template(self, product_image_path, template_path):
        """
        应用模板到产品图片
        @param product_image_path: 产品图片的路径
        @param template_path: 模板图片的路径
        """
        config = TemplateConfig()
        
        # 打开产品图片和模板
        with Image.open(product_image_path) as product_image, Image.open(template_path) as template:
            template_width, template_height = template.size
            
            # 检测产品图片的主体区域
            content_box = self.detect_content_box(product_image)
            if not content_box:
                raise ValueError("无法检测到产品图片的主体内容")
            
            # 裁剪出主体内容
            product_content = product_image.crop(content_box)
            content_width = content_box[2] - content_box[0]
            content_height = content_box[3] - content_box[1]
            
            # 计算最大允许尺寸
            max_width = int(template_width * config.max_width_ratio)
            max_height = int(template_height * config.max_height_ratio)
            
            # 计算缩放比例
            scale = min(max_width / content_width, max_height / content_height)
            
            # 调整主体大小
            new_width = int(content_width * scale)
            new_height = int(content_height * scale)
            product_content = product_content.resize((new_width, new_height), Image.LANCZOS)
            
            # 计算水平位置（居中）
            x = (template_width - new_width) // 2
            
            # 计算垂直位置（在模板高度的65%处）
            y = int(template_height * config.vertical_position) - new_height
            
            # 确保图片不会超出模板边界
            y = max(0, min(y, template_height - new_height))
            
            # 创建最终画布
            final_image = template.copy()
            
            # 粘贴产品图片
            final_image.paste(product_content, (x, y), product_content)
            
            # 生成输出文件名
            filename = os.path.basename(product_image_path)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(self.final_folder, f'final_{base_name}.png')
            
            # 保存结果
            final_image.save(output_path, 'PNG')
            return output_path

    def test_convert_single_psd(self, psd_path):
        """测试转换单个PSD文件"""
        print(f"\n开始测试转换: {psd_path}")
        print(f"文件是否存在: {os.path.exists(psd_path)}")
        
        try:
            print("尝试打开PSD文件...")
            psd = PSDImage.open(psd_path)
            print("PSD文件打开成功")
            
            print("尝试合并图层...")
            image = psd.composite()
            print("图层合并成功")
            
            print("准备保存PNG...")
            filename = os.path.basename(psd_path)
            png_name = os.path.splitext(filename)[0] + '.png'
            output_path = os.path.join(self.png_folder, png_name)
            
            print(f"保存到: {output_path}")
            image.save(output_path)
            print("保存成功")
            
            return output_path
            
        except Exception as e:
            import traceback
            print("\n发生错误:")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print("\n完整错误堆栈:")
            traceback.print_exc()
            return None

    def process_image(self, image_path, template_path):
        """处理任何格式的图片（JPG/PNG）"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"找不到图片: {image_path}")
            
        if not self.validate_template(template_path):
            raise ValueError("无效的模板文件")
            
        try:
            # 打开图片和模板
            with Image.open(image_path) as img, Image.open(template_path) as template:
                # 创建一个透明背景的正方形画布
                size = max(800, 800)  # 确保尺寸至少800x800
                final_image = Image.new('RGBA', (size, size), (0, 0, 0, 0))  # 完全透明的背景
                
                # 计算居中位置
                product_size = min(size * 0.8, max(img.size))  # 产品图占画布80%
                scale = product_size / max(img.size)
                new_size = tuple(int(dim * scale) for dim in img.size)
                
                # 调整产品图大小并确保是RGBA模式
                img = img.resize(new_size, Image.LANCZOS)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 调整模板大小并确保是RGBA模式
                template = template.resize((size, size), Image.LANCZOS)
                if template.mode != 'RGBA':
                    template = template.convert('RGBA')
                
                # 计算居中位置
                pos_x = (size - new_size[0]) // 2
                pos_y = (size - new_size[1]) // 2
                
                # 先放置模板（底层）
                final_image.paste(template, (0, 0), template)
                
                # 再放置产品图（上层）
                final_image.paste(img, (pos_x, pos_y), img)
                
                # 生成输出文件名
                filename = os.path.basename(image_path)
                base_name = os.path.splitext(filename)[0]
                output_path = os.path.join(self.final_folder, f'final_{base_name}.png')
                
                # 保存最终图片，确保保留透明通道
                final_image.save(output_path, 'PNG', optimize=True)
                print(f"已处理: {output_path}")
                return output_path
                
        except Exception as e:
            raise RuntimeError(f"处理失败 {image_path}: {str(e)}")

    def detect_content_box(self, image):
        """检测图片中的主体内容区域"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # 获取alpha通道
        alpha = image.split()[3]
        
        # 获取非透明像素的边界
        bbox = alpha.getbbox()
        if not bbox:
            return None
        
        # 添加一些边距以确保不会裁剪得太紧
        margin = 10
        width, height = image.size
        bbox = (
            max(0, bbox[0] - margin),
            max(0, bbox[1] - margin),
            min(width, bbox[2] + margin),
            min(height, bbox[3] + margin)
        )
        
        return bbox

class TemplateConfig:
    def __init__(self):
        # 产品图片的最大宽度比例（相对于模板宽度）
        self.max_width_ratio = 0.55  # 55%的模板宽度
        
        # 产品图片的最大高度比例（相对于模板高度）
        self.max_height_ratio = 0.6  # 60%的模板高度
        
        # 垂直位置偏移比例（从上方算起）
        self.vertical_position = 0.65  # 在65%的位置
        
        # 水平位置是居中的
        self.horizontal_center = True

def main():
    processor = ImageProcessor()
    
    while True:
        print("\n=== 图片处理工具 ===")
        print("1. 转换PSD到PNG")
        print("2. 应用模板")
        print("3. 一键处理（转换并应用模板）")
        print("4. 退出")
        print("5. 测试单个文件")
        print("6. 处理JPG文件")  # 新增选项
        
        choice = input("\n请选择操作 (1-6): ")
        
        if choice == '1':
            psd_files = [f for f in os.listdir('.') if f.endswith('.psd')]
            if not psd_files:
                print("当前文件夹没有找到PSD文件！")
                continue
                
            print("\n找到以下PSD文件：")
            for i, f in enumerate(psd_files, 1):
                print(f"{i}. {f}")
            
            failed_files = []
            for psd_file in psd_files:
                try:
                    processor.convert_psd_to_png(psd_file)
                except Exception as e:
                    import traceback
                    print(f"\n处理 {psd_file} 时出错:")
                    print(f"错误类型: {type(e).__name__}")
                    print(f"错误信息: {str(e)}")
                    print("详细错误信息:")
                    print(traceback.format_exc())
                    failed_files.append(psd_file)
                    
            if failed_files:
                print("\n以下文件处理失败:")
                for f in failed_files:
                    print(f"- {f}")
                    
        elif choice == '2':
            template_path = input("请输入模板图片路径: ")
            
            try:
                if not processor.validate_template(template_path):
                    continue
                    
                png_files = [f for f in os.listdir(processor.png_folder) if f.endswith('.png')]
                if not png_files:
                    print("没有找到PNG文件！请先转换PSD文件。")
                    continue
                
                failed_files = []
                for png_file in png_files:
                    try:
                        png_path = os.path.join(processor.png_folder, png_file)
                        processor.apply_template(png_path, template_path)
                    except Exception as e:
                        print(f"处理 {png_file} 时出错: {str(e)}")
                        failed_files.append(png_file)
                        
                if failed_files:
                    print("\n以下文件处理失败:")
                    for f in failed_files:
                        print(f"- {f}")
                        
            except Exception as e:
                print(f"模板处理出错: {str(e)}")
                
        elif choice == '3':
            template_path = input("请输入模板图片路径: ")
            if not os.path.exists(template_path):
                print("模板文件不存在！")
                continue
                
            psd_files = [f for f in os.listdir('.') if f.endswith('.psd')]
            if not psd_files:
                print("当前文件夹没有找到PSD文件！")
                continue
                
            for psd_file in psd_files:
                png_path = processor.convert_psd_to_png(psd_file)
                if png_path:
                    processor.apply_template(png_path, template_path)
                    
        elif choice == '4':
            print("感谢使用！")
            break
            
        elif choice == '5':
            psd_file = input("请输入要测试的PSD文件名: ")
            if not os.path.exists(psd_file):
                print(f"文件不存在: {psd_file}")
                continue
            
            result = processor.test_convert_single_psd(psd_file)
            if result:
                print(f"\n测试成功! 输出文件: {result}")
            else:
                print("\n测试失败!")
            
        elif choice == '6':
            template_path = input("请输入模板图片路径: ")
            if not os.path.exists(template_path):
                print("模板文件不存在！")
                continue
                
            jpg_files = [f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.jpeg'))]
            if not jpg_files:
                print("当前文件夹没有找到JPG文件！")
                continue
                
            print("\n找到以下JPG文件：")
            for i, f in enumerate(jpg_files, 1):
                print(f"{i}. {f}")
            
            for jpg_file in jpg_files:
                try:
                    processor.process_image(jpg_file, template_path)
                except Exception as e:
                    print(f"处理 {jpg_file} 时出错: {str(e)}")
                    
        else:
            print("无效的选择，请重试。")

if __name__ == "__main__":
    main() 
