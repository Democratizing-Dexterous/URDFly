# -*- coding: utf-8 -*-
"""
翻译模块 - 支持中英文切换
使用 Qt 的国际化机制实现语言切换功能
"""

from PyQt5.QtCore import QCoreApplication, QTranslator
import os

# 所有翻译字符串
# 格式: "翻译键": {"zh_CN": "中文", "en": "English"}
TRANSLATIONS = {
    # === 窗口标题 ===
    "window_title": {"zh_CN": "URDFly", "en": "URDFly"},

    # === 左侧面板 ===
    "robot_structure": {"zh_CN": "机器人结构：", "en": "Robot Structure:"},
    "select_chain": {"zh_CN": "选择运动链：", "en": "Select Chain:"},
    "links": {"zh_CN": "连杆：", "en": "Links:"},
    "open_urdf": {"zh_CN": "打开 URDF", "en": "Open URDF"},
    "edit_urdf": {"zh_CN": "编辑 URDF", "en": "Edit URDF"},
    "edit_urdf_tooltip": {"zh_CN": "在 XML 编辑器中打开当前 URDF 文件", "en": "Open the current URDF file in an XML editor"},
    "show_mdh": {"zh_CN": "显示 MDH 参数", "en": "Show MDH Parameters"},
    "decompose_collision": {"zh_CN": "凸分解碰撞体", "en": "Decompose As Collision"},
    "set_joints": {"zh_CN": "设置关节", "en": "Set Joints"},

    # === 透明度控制 ===
    "transparency": {"zh_CN": "透明度：", "en": "Transparency:"},

    # === 显示设置 ===
    "visibility_settings": {"zh_CN": "显示设置", "en": "Visibility"},
    "show_link_frames": {"zh_CN": "显示连杆坐标系", "en": "Show Link Frames"},
    "show_mdh_frames": {"zh_CN": "显示 MDH 坐标系", "en": "Show MDH Frames"},
    "show_collision": {"zh_CN": "显示碰撞体", "en": "Show Collision"},

    # === 关节控制 ===
    "joints_control": {"zh_CN": "关节控制", "en": "Joints Control"},
    "adjust_joint_angles": {"zh_CN": "调整关节角度：", "en": "Adjust joint angles:"},
    "reset": {"zh_CN": "重置", "en": "Reset"},
    "random": {"zh_CN": "随机", "en": "Random"},

    # === 当前文件 ===
    "current_file": {"zh_CN": "当前文件：", "en": "Current File:"},
    "current_file_none": {"zh_CN": "无", "en": "None"},
    "no_file_loaded": {"zh_CN": "没有加载文件", "en": "No file loaded"},

    # === 按钮 ===
    "btn_cancel": {"zh_CN": "取消", "en": "Cancel"},
    "btn_ok": {"zh_CN": "确定", "en": "OK"},

    # === MDH 对话框 ===
    "mdh_title": {"zh_CN": "MDH 参数", "en": "MDH Parameters"},
    "mdh_parameters": {"zh_CN": "MDH 参数", "en": "MDH Parameters"},
    "joint": {"zh_CN": "关节", "en": "Joint"},
    "forward_kinematics": {"zh_CN": "正运动学", "en": "Forward Kinematics"},
    "jacobian": {"zh_CN": "雅可比", "en": "Jacobian"},
    "dynamic_base_regressor": {"zh_CN": "动力学基回归器", "en": "Dynamic Base Regressor"},
    "save_mdh": {"zh_CN": "保存 MDH", "en": "Save MDH"},
    "header_file_or_python_usage": {"zh_CN": "头文件或 Python 使用", "en": "Header File or Python Usage"},
    "cpp_source_file": {"zh_CN": "C++ 源文件", "en": ".cpp Source File"},
    "copy": {"zh_CN": "复制", "en": "Copy"},

    # === 凸分解对话框 ===
    "decomp_title": {"zh_CN": "凸分解碰撞体", "en": "Decompose Collision Meshes"},
    "mesh_file": {"zh_CN": "网格文件", "en": "Mesh File"},
    "max_convex_hulls": {"zh_CN": "最大凸包数", "en": "maxConvexHulls"},
    "decomposition_complete": {"zh_CN": "分解完成", "en": "Decomposition Complete"},
    "decomposition_success": {"zh_CN": "成功分解 {} 个网格文件。", "en": "Successfully decomposed {} mesh files."},
    "decomposition_error": {"zh_CN": "分解错误", "en": "Decomposition Error"},
    "decomposition_error_msg": {"zh_CN": "分解过程中出错：{}", "en": "Error during decomposition: {}"},

    # === XML 编辑器 ===
    "urdf_editor": {"zh_CN": "URDF 编辑器", "en": "URDF Editor"},
    "save_as": {"zh_CN": "另存为", "en": "Save As"},
    "update": {"zh_CN": "更新", "en": "Update"},
    "update_tooltip": {"zh_CN": "更新查看器中的模型而不保存文件", "en": "Update the model in the viewer without saving the file"},
    "search": {"zh_CN": "搜索：", "en": "Search:"},
    "search_placeholder": {"zh_CN": "输入搜索文本...", "en": "Enter search text..."},
    "previous": {"zh_CN": "上一个", "en": "Previous"},
    "previous_tooltip": {"zh_CN": "查找上一个出现位置 (Shift+F3)", "en": "Find previous occurrence (Shift+F3)"},
    "next": {"zh_CN": "下一个", "en": "Next"},
    "next_tooltip": {"zh_CN": "查找下一个出现位置 (F3)", "en": "Find next occurrence (F3)"},
    "precision": {"zh_CN": "精度：", "en": "Precision:"},
    "pi_tooltip": {"zh_CN": "在光标位置插入 π 值", "en": "Insert π value at cursor position"},
    "pi_half_tooltip": {"zh_CN": "在光标位置插入 π/2 值", "en": "Insert π/2 value at cursor position"},
    "pi_quarter_tooltip": {"zh_CN": "在光标位置插入 π/4 值", "en": "Insert π/4 value at cursor position"},
    "precision_tooltip": {"zh_CN": "π 值的小数位数", "en": "Number of decimal places for π values"},
    "header_placeholder": {"zh_CN": "头文件或 Python 使用内容将显示在这里...", "en": "Header file or Python usage content will be displayed here..."},
    "cpp_placeholder": {"zh_CN": "源文件内容将显示在这里...", "en": "Source file content will be displayed here..."},

    # === 警告/错误/信息 ===
    "warning": {"zh_CN": "警告", "en": "Warning"},
    "error": {"zh_CN": "错误", "en": "Error"},
    "info": {"zh_CN": "提示", "en": "Info"},
    "success": {"zh_CN": "成功", "en": "Success"},
    "search": {"zh_CN": "搜索", "en": "Search"},
    "no_more_occurrences": {"zh_CN": "没有找到更多匹配项。", "en": "No more occurrences found."},
    "update_callback_not_set": {"zh_CN": "更新回调未设置。", "en": "Update callback not set."},

    # === 文件操作 ===
    "load_urdf_failed": {"zh_CN": "加载 URDF 文件失败: {}", "en": "Failed to load URDF file: {}"},
    "load_model_failed": {"zh_CN": "加载模型 {} 失败: {}", "en": "Failed to load model {}: {}"},
    "file_saved_successfully": {"zh_CN": "文件保存成功。", "en": "File saved successfully."},
    "failed_to_load_file": {"zh_CN": "加载文件失败：{}", "en": "Failed to load file: {}"},
    "failed_to_save_file": {"zh_CN": "保存文件失败：{}", "en": "Failed to save file: {}"},
    "failed_to_save_mdh": {"zh_CN": "保存 MDH 参数失败：\n{}", "en": "Failed to save MDH parameters:\n{}"},
    "mdh_saved": {"zh_CN": "MDH 参数已保存到:\n{}", "en": "MDH parameters saved to:\n{}"},
    "header_copied": {"zh_CN": "头代码已复制到剪贴板！", "en": "Header code copied to clipboard!"},
    "source_copied": {"zh_CN": "源代码已复制到剪贴板！", "en": "Source code copied to clipboard!"},
    "copied": {"zh_CN": "已复制", "en": "Copied"},

    # === 对话框标题 ===
    "dialog_open_urdf": {"zh_CN": "打开 URDF 文件", "en": "Open URDF File"},
    "dialog_urdf_filter": {"zh_CN": "URDF 文件 (*.urdf)", "en": "URDF Files (*.urdf)"},
    "dialog_save_file_as": {"zh_CN": "文件另存为", "en": "Save File As"},
    "dialog_save_mdh": {"zh_CN": "保存 MDH 参数", "en": "Save MDH Parameters"},
    "dialog_text_files": {"zh_CN": "文本文件 (*.txt)", "en": "Text Files (*.txt)"},

    # === 语言切换 ===
    "language": {"zh_CN": "语言：", "en": "Language:"},
    "lang_zh": {"zh_CN": "简体中文", "en": "Simplified Chinese"},
    "lang_en": {"zh_CN": "English", "en": "English"},

    # === 提示信息 ===
    "please_load_urdf_first": {"zh_CN": "请先加载 URDF 文件。", "en": "Please load a URDF file first."},
    "please_load_urdf_edit": {"zh_CN": "请先加载 URDF 文件。[编辑]", "en": "Please load a URDF file first. [Edit]"},
    "please_load_urdf_mdh": {"zh_CN": "请先加载 URDF 文件。[MDH]", "en": "Please load a URDF file first. [MDH]"},
    "please_load_urdf_show_mdh": {"zh_CN": "请先加载 URDF 文件。[显示 MDH]", "en": "Please load a URDF file first. [Show MDH]"},
    "please_select_chain_first": {"zh_CN": "请先选择一个运动链。", "en": "Please select a chain first."},
    "please_select_chain_mdh": {"zh_CN": "请先选择一个运动链以查看 MDH 参数。", "en": "Please select a kinematic chain to view MDH parameters."},
    "no_collision_meshes": {"zh_CN": "没有可用的碰撞网格。请先加载 URDF 文件。", "en": "No collision meshes available. Please load a URDF file first."},
    "no_revolute_joints": {"zh_CN": "没有可用的旋转关节。请先加载 URDF 文件。", "en": "No revolute joints available. Please load a URDF file first."},

    # === 运动链 ===
    "chain_pattern": {"zh_CN": "运动链 {}: {}", "en": "Chain {}: {}"},

    # === 设置关节对话框 ===
    "set_joints_title": {"zh_CN": "设置关节角度", "en": "Set Joint Angles"},
    "enter_joint_angles": {"zh_CN": "输入关节角度（用逗号或空格分隔）：", "en": "Enter joint angles (comma or space separated):"},
    "units": {"zh_CN": "单位：", "en": "Units:"},
    "apply": {"zh_CN": "应用", "en": "Apply"},
    "please_input_angles": {"zh_CN": "请输入角度值。", "en": "Please input angles."},
    "invalid_number": {"zh_CN": "输入列表中包含无效数字。", "en": "Invalid number in input list."},
    "expected_values": {"zh_CN": "需要 {} 个值，收到 {} 个。", "en": "Expected {} values, got {}."},

    # === 保存 MDH 文件内容 ===
    "mdh_file_header": {"zh_CN": "MDH 参数 - {}", "en": "MDH Parameters for {}"},
    "mdh_column_header": {"zh_CN": "{:<10} {:<12} {:<12} {:<12} {:<12}", "en": "{:<10} {:<12} {:<12} {:<12} {:<12}"},
    "mdh_total_joints": {"zh_CN": "总关节数：{}", "en": "Total joints: {}"},

    # === 表头 ===
    "theta_rad": {"zh_CN": "θ (rad)", "en": "θ (rad)"},
    "alpha_rad": {"zh_CN": "α (rad)", "en": "α (rad)"},
}


class TranslationManager:
    """翻译管理器 - 处理语言切换和翻译获取"""

    def __init__(self):
        self.current_language = "zh_CN"  # 默认中文
        self.translator = None
        self.available_languages = ["zh_CN", "en"]

    def tr(self, key, default=None, *args):
        """
        获取指定键的翻译
        :param key: 翻译键
        :param default: 默认值（如果键不存在，返回键本身）
        :param args: 格式化参数
        """
        if key not in TRANSLATIONS:
            result = default if default is not None else key
        else:
            result = TRANSLATIONS[key].get(self.current_language, default if default is not None else key)

        # 支持格式化参数，如 "Hello {}" -> "Hello World"
        if args:
            try:
                return result.format(*args)
            except (IndexError, KeyError, ValueError):
                return result
        return result

    def set_language(self, lang_code, main_window=None):
        """
        切换语言
        :param lang_code: 语言代码 ('zh_CN' 或 'en')
        :param main_window: 主窗口对象（用于重新翻译UI）
        """
        if lang_code not in self.available_languages:
            print(f"Warning: Unsupported language code: {lang_code}")
            return False

        old_lang = self.current_language
        self.current_language = lang_code

        if main_window:
            # 重新翻译整个界面
            self.retranslate_ui(main_window)

        print(f"Language changed from {old_lang} to {lang_code}")
        return True

    def retranslate_ui(self, main_window):
        """重新翻译主窗口的所有UI元素"""
        # 更新窗口标题
        main_window.setWindowTitle(self.tr("window_title"))

        # 更新机器人结构标签
        if hasattr(main_window, 'robot_structure_label'):
            main_window.robot_structure_label.setText(self.tr("robot_structure"))

        # 更新选择运动链标签
        if hasattr(main_window, 'select_chain_label'):
            main_window.select_chain_label.setText(self.tr("select_chain"))

        # 更新连杆标签
        if hasattr(main_window, 'links_label'):
            main_window.links_label.setText(self.tr("links"))

        # 更新当前文件标签
        if hasattr(main_window, 'current_file_label'):
            if main_window.current_urdf_file:
                import os
                filename = os.path.basename(main_window.current_urdf_file)
                main_window.current_file_label.setText(self.tr("current_file") + " " + filename)
            else:
                main_window.current_file_label.setText(self.tr("current_file") + " " + self.tr("current_file_none"))

        # 更新按钮
        if hasattr(main_window, 'btn_open'):
            main_window.btn_open.setText(self.tr("open_urdf"))
        if hasattr(main_window, 'btn_edit'):
            main_window.btn_edit.setText(self.tr("edit_urdf"))
            main_window.btn_edit.setToolTip(self.tr("edit_urdf_tooltip"))
        if hasattr(main_window, 'btn_mdh'):
            main_window.btn_mdh.setText(self.tr("show_mdh"))
        if hasattr(main_window, 'btn_decomp'):
            main_window.btn_decomp.setText(self.tr("decompose_collision"))
        if hasattr(main_window, 'btn_set_joints'):
            main_window.btn_set_joints.setText(self.tr("set_joints"))

        # 更新透明度标签
        if hasattr(main_window, 'transparency_label'):
            main_window.transparency_label.setText(self.tr("transparency"))

        # 更新显示设置组
        if hasattr(main_window, 'visibility_group'):
            main_window.visibility_group.setTitle(self.tr("visibility_settings"))

        if hasattr(main_window, 'cb_link_frames'):
            main_window.cb_link_frames.setText(self.tr("show_link_frames"))
        if hasattr(main_window, 'cb_mdh_frames'):
            main_window.cb_mdh_frames.setText(self.tr("show_mdh_frames"))
        if hasattr(main_window, 'cb_collision'):
            main_window.cb_collision.setText(self.tr("show_collision"))

        # 更新关节控制标签
        if hasattr(main_window, 'joint_label'):
            main_window.joint_label.setText(self.tr("adjust_joint_angles"))

        # 更新关节控制组
        if hasattr(main_window, 'joint_group'):
            main_window.joint_group.setTitle(self.tr("joints_control"))

        # 更新重置和随机按钮
        if hasattr(main_window, 'btn_reset'):
            main_window.btn_reset.setText(self.tr("reset"))
        if hasattr(main_window, 'btn_random'):
            main_window.btn_random.setText(self.tr("random"))

        # 更新语言标签
        if hasattr(main_window, 'lang_label'):
            main_window.lang_label.setText(self.tr("language"))

        # 更新语言选择下拉框
        if hasattr(main_window, 'language_combo'):
            main_window.language_combo.setItemText(0, self.tr("lang_zh"))
            main_window.language_combo.setItemText(1, self.tr("lang_en"))

    @staticmethod
    def get_available_languages():
        """获取可用的语言列表"""
        return [
            {"code": "zh_CN", "name": "简体中文", "native_name": "简体中文"},
            {"code": "en", "name": "English", "native_name": "English"},
        ]


# 全局翻译实例
_translation_manager = TranslationManager()


def tr(key, default=None, *args):
    """
    全局翻译函数的快捷方式
    :param key: 翻译键
    :param default: 默认值
    :param args: 格式化参数
    :return: 翻译后的字符串
    """
    return _translation_manager.tr(key, default, *args)


def get_translation_manager():
    """获取全局翻译管理器实例"""
    return _translation_manager
